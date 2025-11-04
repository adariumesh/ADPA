"""
AWS Glue ETL Script for Data Profiling
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json


def create_glue_context():
    """Initialize Glue context and job."""
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'input_path',
        'output_path',
        'database_name',
        'table_name'
    ])
    
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    return glueContext, spark, job, args


def profile_dataset(spark, df: DataFrame) -> dict:
    """
    Generate comprehensive data profile for the dataset.
    
    Args:
        spark: Spark session
        df: Input DataFrame
        
    Returns:
        Dictionary with profiling results
    """
    print("Starting data profiling...")
    
    # Basic statistics
    row_count = df.count()
    column_count = len(df.columns)
    
    print(f"Dataset shape: {row_count} rows, {column_count} columns")
    
    # Column analysis
    columns_info = []
    numeric_columns = []
    categorical_columns = []
    
    for col_name, col_type in df.dtypes:
        col_info = {
            'name': col_name,
            'type': col_type,
            'null_count': df.filter(col(col_name).isNull()).count(),
            'distinct_count': df.select(col_name).distinct().count()
        }
        
        # Calculate null percentage
        col_info['null_percentage'] = (col_info['null_count'] / row_count) * 100
        
        # Type-specific analysis
        if col_type in ['int', 'bigint', 'double', 'float', 'decimal']:
            numeric_columns.append(col_name)
            
            # Numeric statistics
            stats = df.select(
                min(col(col_name)).alias('min'),
                max(col(col_name)).alias('max'),
                mean(col(col_name)).alias('mean'),
                stddev(col(col_name)).alias('stddev')
            ).collect()[0]
            
            col_info.update({
                'min_value': float(stats['min']) if stats['min'] is not None else None,
                'max_value': float(stats['max']) if stats['max'] is not None else None,
                'mean_value': float(stats['mean']) if stats['mean'] is not None else None,
                'std_value': float(stats['stddev']) if stats['stddev'] is not None else None
            })
            
        else:
            categorical_columns.append(col_name)
            
            # Top values for categorical columns
            if col_info['distinct_count'] <= 100:  # Only for low cardinality
                top_values = df.groupBy(col_name) \
                              .count() \
                              .orderBy(desc('count')) \
                              .limit(10) \
                              .collect()
                
                col_info['top_values'] = [
                    {'value': str(row[col_name]), 'count': row['count']}
                    for row in top_values
                ]
        
        columns_info.append(col_info)
    
    # Data quality assessment
    total_cells = row_count * column_count
    total_nulls = sum(col_info['null_count'] for col_info in columns_info)
    completeness_score = 1 - (total_nulls / total_cells) if total_cells > 0 else 0
    
    # Duplicate analysis
    duplicate_count = row_count - df.distinct().count()
    
    # Memory usage estimation
    size_estimate = df.rdd.map(lambda row: len(str(row))).sum()
    
    profile = {
        'basic_stats': {
            'row_count': row_count,
            'column_count': column_count,
            'numeric_columns': len(numeric_columns),
            'categorical_columns': len(categorical_columns),
            'total_null_values': total_nulls,
            'duplicate_rows': duplicate_count,
            'estimated_size_bytes': size_estimate
        },
        'data_quality': {
            'completeness_score': round(completeness_score, 4),
            'completeness_percentage': round(completeness_score * 100, 2),
            'duplicate_percentage': round((duplicate_count / row_count) * 100, 2) if row_count > 0 else 0
        },
        'columns': columns_info,
        'column_types': {
            'numeric_columns': numeric_columns,
            'categorical_columns': categorical_columns
        }
    }
    
    print(f"Data profiling completed. Quality score: {completeness_score:.4f}")
    
    return profile


def detect_data_issues(spark, df: DataFrame, profile: dict) -> dict:
    """
    Detect potential data quality issues.
    
    Args:
        spark: Spark session
        df: Input DataFrame
        profile: Data profile
        
    Returns:
        Dictionary with detected issues
    """
    print("Detecting data quality issues...")
    
    issues = {
        'high_missing_values': [],
        'high_cardinality': [],
        'potential_outliers': [],
        'data_type_inconsistencies': [],
        'duplicate_columns': []
    }
    
    # Check for high missing values
    for col_info in profile['columns']:
        if col_info['null_percentage'] > 30:
            issues['high_missing_values'].append({
                'column': col_info['name'],
                'null_percentage': col_info['null_percentage']
            })
    
    # Check for high cardinality categorical columns
    for col_info in profile['columns']:
        if col_info['name'] in profile['column_types']['categorical_columns']:
            cardinality_ratio = col_info['distinct_count'] / profile['basic_stats']['row_count']
            if cardinality_ratio > 0.8:  # More than 80% unique values
                issues['high_cardinality'].append({
                    'column': col_info['name'],
                    'distinct_count': col_info['distinct_count'],
                    'cardinality_ratio': round(cardinality_ratio, 4)
                })
    
    # Check for potential outliers in numeric columns (simplified IQR method)
    for col_name in profile['column_types']['numeric_columns']:
        try:
            # Calculate quartiles
            quartiles = df.select(
                expr(f"percentile_approx({col_name}, 0.25)").alias('q1'),
                expr(f"percentile_approx({col_name}, 0.75)").alias('q3')
            ).collect()[0]
            
            if quartiles['q1'] is not None and quartiles['q3'] is not None:
                q1, q3 = quartiles['q1'], quartiles['q3']
                iqr = q3 - q1
                
                if iqr > 0:
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outlier_count = df.filter(
                        (col(col_name) < lower_bound) | (col(col_name) > upper_bound)
                    ).count()
                    
                    if outlier_count > 0:
                        outlier_percentage = (outlier_count / profile['basic_stats']['row_count']) * 100
                        issues['potential_outliers'].append({
                            'column': col_name,
                            'outlier_count': outlier_count,
                            'outlier_percentage': round(outlier_percentage, 2)
                        })
        except:
            # Skip if calculation fails
            pass
    
    # Check for duplicate column names (case insensitive)
    column_names_lower = [col_name.lower() for col_name in df.columns]
    if len(column_names_lower) != len(set(column_names_lower)):
        issues['duplicate_columns'] = [
            name for name in set(column_names_lower) 
            if column_names_lower.count(name) > 1
        ]
    
    print(f"Data quality issues detected: {len(issues['high_missing_values'])} high missing, "
          f"{len(issues['potential_outliers'])} outlier columns")
    
    return issues


def save_profile_results(spark, profile: dict, issues: dict, output_path: str):
    """
    Save profiling results to S3.
    
    Args:
        spark: Spark session
        profile: Data profile
        issues: Detected issues
        output_path: S3 output path
    """
    print(f"Saving profiling results to: {output_path}")
    
    # Combine profile and issues
    results = {
        'profile': profile,
        'issues': issues,
        'recommendations': generate_recommendations(profile, issues)
    }
    
    # Convert to JSON and save
    results_json = json.dumps(results, indent=2, default=str)
    
    # Create DataFrame with results
    results_df = spark.createDataFrame([(results_json,)], ['profile_results'])
    
    # Save to S3
    results_df.coalesce(1).write.mode('overwrite').text(output_path)
    
    print("Profiling results saved successfully")


def generate_recommendations(profile: dict, issues: dict) -> list:
    """
    Generate recommendations based on profile and issues.
    
    Args:
        profile: Data profile
        issues: Detected issues
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Missing values recommendations
    if issues['high_missing_values']:
        recommendations.append({
            'type': 'missing_values',
            'priority': 'high',
            'message': f"Consider imputation or removal for {len(issues['high_missing_values'])} columns with high missing values"
        })
    
    # High cardinality recommendations
    if issues['high_cardinality']:
        recommendations.append({
            'type': 'high_cardinality',
            'priority': 'medium',
            'message': f"Consider encoding or binning for {len(issues['high_cardinality'])} high cardinality columns"
        })
    
    # Outlier recommendations
    if issues['potential_outliers']:
        recommendations.append({
            'type': 'outliers',
            'priority': 'medium',
            'message': f"Consider outlier treatment for {len(issues['potential_outliers'])} columns"
        })
    
    # Data size recommendations
    row_count = profile['basic_stats']['row_count']
    if row_count > 1000000:
        recommendations.append({
            'type': 'performance',
            'priority': 'medium',
            'message': "Large dataset detected. Consider partitioning or sampling for faster processing"
        })
    
    # Data quality recommendations
    completeness = profile['data_quality']['completeness_score']
    if completeness < 0.8:
        recommendations.append({
            'type': 'data_quality',
            'priority': 'high',
            'message': f"Low data completeness ({completeness*100:.1f}%). Investigate data collection process"
        })
    
    return recommendations


def main():
    """Main ETL execution."""
    try:
        # Initialize Glue context
        glueContext, spark, job, args = create_glue_context()
        
        print(f"Starting data profiling job: {args['JOB_NAME']}")
        print(f"Input path: {args['input_path']}")
        print(f"Output path: {args['output_path']}")
        
        # Read input data
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(args['input_path'])
        
        print(f"Data loaded successfully: {df.count()} rows, {len(df.columns)} columns")
        
        # Generate data profile
        profile = profile_dataset(spark, df)
        
        # Detect data issues
        issues = detect_data_issues(spark, df, profile)
        
        # Save results
        save_profile_results(spark, profile, issues, args['output_path'])
        
        # Create/update data catalog table if specified
        if 'database_name' in args and 'table_name' in args:
            print(f"Updating data catalog: {args['database_name']}.{args['table_name']}")
            # This would typically be done via Glue client, not in the ETL script
        
        print("Data profiling job completed successfully")
        
        job.commit()
        
    except Exception as e:
        print(f"Job failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()