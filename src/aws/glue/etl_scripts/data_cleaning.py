"""
AWS Glue ETL Script for Data Cleaning
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
        'cleaning_config'
    ])
    
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    return glueContext, spark, job, args


def parse_cleaning_config(config_str: str) -> dict:
    """Parse cleaning configuration from string."""
    try:
        config = json.loads(config_str)
    except:
        # Default configuration
        config = {
            'remove_duplicates': True,
            'missing_value_strategy': 'median',
            'outlier_treatment': 'cap',
            'data_type_conversion': True,
            'outlier_threshold': 3.0
        }
    
    return config


def remove_duplicates(df: DataFrame) -> tuple[DataFrame, dict]:
    """
    Remove duplicate rows from DataFrame.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Tuple of (cleaned DataFrame, statistics)
    """
    print("Removing duplicate rows...")
    
    initial_count = df.count()
    cleaned_df = df.distinct()
    final_count = cleaned_df.count()
    
    duplicates_removed = initial_count - final_count
    
    stats = {
        'initial_rows': initial_count,
        'final_rows': final_count,
        'duplicates_removed': duplicates_removed,
        'duplicate_percentage': round((duplicates_removed / initial_count) * 100, 2) if initial_count > 0 else 0
    }
    
    print(f"Removed {duplicates_removed} duplicate rows ({stats['duplicate_percentage']}%)")
    
    return cleaned_df, stats


def handle_missing_values(df: DataFrame, strategy: str = 'median') -> tuple[DataFrame, dict]:
    """
    Handle missing values in DataFrame.
    
    Args:
        df: Input DataFrame
        strategy: Strategy for handling missing values ('drop', 'median', 'mode', 'zero')
        
    Returns:
        Tuple of (cleaned DataFrame, statistics)
    """
    print(f"Handling missing values using strategy: {strategy}")
    
    # Calculate initial missing values
    initial_missing = {}
    for col_name in df.columns:
        missing_count = df.filter(col(col_name).isNull()).count()
        initial_missing[col_name] = missing_count
    
    total_initial_missing = sum(initial_missing.values())
    
    cleaned_df = df
    
    if strategy == 'drop':
        # Drop rows with any missing values
        cleaned_df = df.dropna()
        
    elif strategy == 'median':
        # Fill numeric columns with median, categorical with mode
        for col_name, col_type in df.dtypes:
            if initial_missing[col_name] > 0:
                if col_type in ['int', 'bigint', 'double', 'float', 'decimal']:
                    # Use median for numeric columns
                    median_val = df.select(expr(f"percentile_approx({col_name}, 0.5)").alias('median')).collect()[0]['median']
                    if median_val is not None:
                        cleaned_df = cleaned_df.fillna({col_name: median_val})
                else:
                    # Use mode for categorical columns
                    mode_result = df.groupBy(col_name).count().orderBy(desc('count')).first()
                    if mode_result and mode_result[col_name] is not None:
                        cleaned_df = cleaned_df.fillna({col_name: mode_result[col_name]})
    
    elif strategy == 'mode':
        # Fill all columns with mode
        for col_name in df.columns:
            if initial_missing[col_name] > 0:
                mode_result = df.groupBy(col_name).count().orderBy(desc('count')).first()
                if mode_result and mode_result[col_name] is not None:
                    cleaned_df = cleaned_df.fillna({col_name: mode_result[col_name]})
    
    elif strategy == 'zero':
        # Fill numeric columns with 0, categorical with 'Unknown'
        fill_values = {}
        for col_name, col_type in df.dtypes:
            if initial_missing[col_name] > 0:
                if col_type in ['int', 'bigint', 'double', 'float', 'decimal']:
                    fill_values[col_name] = 0
                else:
                    fill_values[col_name] = 'Unknown'
        
        cleaned_df = cleaned_df.fillna(fill_values)
    
    # Calculate final missing values
    final_missing = {}
    for col_name in cleaned_df.columns:
        missing_count = cleaned_df.filter(col(col_name).isNull()).count()
        final_missing[col_name] = missing_count
    
    total_final_missing = sum(final_missing.values())
    
    stats = {
        'strategy': strategy,
        'initial_missing_values': total_initial_missing,
        'final_missing_values': total_final_missing,
        'missing_values_handled': total_initial_missing - total_final_missing,
        'columns_with_missing': len([col for col, count in initial_missing.items() if count > 0])
    }
    
    print(f"Handled {stats['missing_values_handled']} missing values")
    
    return cleaned_df, stats


def handle_outliers(df: DataFrame, threshold: float = 3.0, treatment: str = 'cap') -> tuple[DataFrame, dict]:
    """
    Handle outliers in numeric columns.
    
    Args:
        df: Input DataFrame
        threshold: IQR multiplier threshold
        treatment: Treatment method ('cap', 'remove')
        
    Returns:
        Tuple of (cleaned DataFrame, statistics)
    """
    print(f"Handling outliers using {treatment} method with threshold {threshold}")
    
    cleaned_df = df
    outliers_handled = 0
    columns_processed = []
    
    # Get numeric columns
    numeric_columns = [col_name for col_name, col_type in df.dtypes 
                      if col_type in ['int', 'bigint', 'double', 'float', 'decimal']]
    
    for col_name in numeric_columns:
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
                    lower_bound = q1 - threshold * iqr
                    upper_bound = q3 + threshold * iqr
                    
                    # Count outliers
                    outlier_count = cleaned_df.filter(
                        (col(col_name) < lower_bound) | (col(col_name) > upper_bound)
                    ).count()
                    
                    if outlier_count > 0:
                        outliers_handled += outlier_count
                        columns_processed.append(col_name)
                        
                        if treatment == 'cap':
                            # Cap outliers to bounds
                            cleaned_df = cleaned_df.withColumn(
                                col_name,
                                when(col(col_name) < lower_bound, lower_bound)
                                .when(col(col_name) > upper_bound, upper_bound)
                                .otherwise(col(col_name))
                            )
                        elif treatment == 'remove':
                            # Remove outlier rows
                            cleaned_df = cleaned_df.filter(
                                (col(col_name) >= lower_bound) & (col(col_name) <= upper_bound)
                            )
        except:
            # Skip if calculation fails
            continue
    
    stats = {
        'treatment_method': treatment,
        'threshold': threshold,
        'outliers_handled': outliers_handled,
        'columns_processed': len(columns_processed),
        'processed_columns': columns_processed
    }
    
    print(f"Handled {outliers_handled} outliers in {len(columns_processed)} columns")
    
    return cleaned_df, stats


def convert_data_types(df: DataFrame) -> tuple[DataFrame, dict]:
    """
    Optimize data types for better performance.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Tuple of (cleaned DataFrame, statistics)
    """
    print("Converting and optimizing data types...")
    
    cleaned_df = df
    conversions = []
    
    for col_name, col_type in df.dtypes:
        original_type = col_type
        
        # Try to optimize numeric types
        if col_type == 'string':
            # Try to convert string columns to numeric if possible
            try:
                # Sample some values to check if they're numeric
                sample_values = df.select(col_name).filter(col(col_name).isNotNull()).limit(100).collect()
                
                if sample_values:
                    # Check if all non-null values can be converted to numbers
                    numeric_convertible = True
                    for row in sample_values[:10]:  # Check first 10 non-null values
                        try:
                            float(row[col_name])
                        except (ValueError, TypeError):
                            numeric_convertible = False
                            break
                    
                    if numeric_convertible:
                        # Convert to double
                        cleaned_df = cleaned_df.withColumn(
                            col_name, 
                            col(col_name).cast(DoubleType())
                        )
                        conversions.append({
                            'column': col_name,
                            'from': original_type,
                            'to': 'double'
                        })
            except:
                # Skip conversion if it fails
                pass
        
        # Optimize integer types
        elif col_type in ['bigint']:
            # Check if values fit in smaller integer type
            try:
                min_max = df.select(
                    min(col(col_name)).alias('min_val'),
                    max(col(col_name)).alias('max_val')
                ).collect()[0]
                
                if min_max['min_val'] is not None and min_max['max_val'] is not None:
                    min_val, max_val = min_max['min_val'], min_max['max_val']
                    
                    # Check if fits in int
                    if -2147483648 <= min_val <= 2147483647 and -2147483648 <= max_val <= 2147483647:
                        cleaned_df = cleaned_df.withColumn(
                            col_name,
                            col(col_name).cast(IntegerType())
                        )
                        conversions.append({
                            'column': col_name,
                            'from': original_type,
                            'to': 'int'
                        })
            except:
                pass
    
    # Clean string columns (trim whitespace, handle common null representations)
    string_columns = [col_name for col_name, col_type in cleaned_df.dtypes if col_type == 'string']
    
    for col_name in string_columns:
        cleaned_df = cleaned_df.withColumn(
            col_name,
            when(
                col(col_name).isin(['', 'null', 'NULL', 'None', 'NONE', 'N/A', 'n/a', 'NA']),
                lit(None)
            ).otherwise(trim(col(col_name)))
        )
    
    stats = {
        'conversions_made': len(conversions),
        'conversions': conversions,
        'string_columns_cleaned': len(string_columns)
    }
    
    print(f"Made {len(conversions)} data type conversions")
    
    return cleaned_df, stats


def validate_cleaned_data(df: DataFrame) -> dict:
    """
    Validate the cleaned dataset.
    
    Args:
        df: Cleaned DataFrame
        
    Returns:
        Validation results
    """
    print("Validating cleaned data...")
    
    row_count = df.count()
    column_count = len(df.columns)
    
    # Check for remaining missing values
    missing_values = {}
    for col_name in df.columns:
        missing_count = df.filter(col(col_name).isNull()).count()
        missing_values[col_name] = missing_count
    
    total_missing = sum(missing_values.values())
    
    # Check data types
    data_types = dict(df.dtypes)
    
    # Check for duplicates
    duplicate_count = row_count - df.distinct().count()
    
    validation = {
        'row_count': row_count,
        'column_count': column_count,
        'total_missing_values': total_missing,
        'completeness_score': 1 - (total_missing / (row_count * column_count)) if row_count * column_count > 0 else 0,
        'duplicate_rows': duplicate_count,
        'data_types': data_types,
        'validation_passed': total_missing == 0 and duplicate_count == 0
    }
    
    print(f"Validation completed. Completeness: {validation['completeness_score']:.4f}")
    
    return validation


def save_cleaning_results(spark, df: DataFrame, stats: dict, output_path: str):
    """
    Save cleaned data and statistics.
    
    Args:
        spark: Spark session
        df: Cleaned DataFrame
        stats: Cleaning statistics
        output_path: Output path
    """
    print(f"Saving cleaned data to: {output_path}")
    
    # Save cleaned data
    df.coalesce(10).write.mode('overwrite').option('header', 'true').csv(f"{output_path}/data")
    
    # Save statistics
    stats_json = json.dumps(stats, indent=2, default=str)
    stats_df = spark.createDataFrame([(stats_json,)], ['cleaning_stats'])
    stats_df.coalesce(1).write.mode('overwrite').text(f"{output_path}/stats")
    
    print("Cleaned data and statistics saved successfully")


def main():
    """Main ETL execution."""
    try:
        # Initialize Glue context
        glueContext, spark, job, args = create_glue_context()
        
        print(f"Starting data cleaning job: {args['JOB_NAME']}")
        print(f"Input path: {args['input_path']}")
        print(f"Output path: {args['output_path']}")
        
        # Parse cleaning configuration
        config = parse_cleaning_config(args.get('cleaning_config', '{}'))
        print(f"Cleaning configuration: {config}")
        
        # Read input data
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(args['input_path'])
        
        print(f"Data loaded successfully: {df.count()} rows, {len(df.columns)} columns")
        
        # Initialize cleaning statistics
        cleaning_stats = {
            'initial_shape': [df.count(), len(df.columns)],
            'cleaning_config': config
        }
        
        # Step 1: Remove duplicates
        if config.get('remove_duplicates', True):
            df, duplicate_stats = remove_duplicates(df)
            cleaning_stats['duplicate_removal'] = duplicate_stats
        
        # Step 2: Handle missing values
        missing_strategy = config.get('missing_value_strategy', 'median')
        df, missing_stats = handle_missing_values(df, missing_strategy)
        cleaning_stats['missing_value_handling'] = missing_stats
        
        # Step 3: Handle outliers
        if config.get('outlier_treatment', 'cap') != 'none':
            outlier_threshold = config.get('outlier_threshold', 3.0)
            outlier_treatment = config.get('outlier_treatment', 'cap')
            df, outlier_stats = handle_outliers(df, outlier_threshold, outlier_treatment)
            cleaning_stats['outlier_handling'] = outlier_stats
        
        # Step 4: Convert data types
        if config.get('data_type_conversion', True):
            df, type_stats = convert_data_types(df)
            cleaning_stats['data_type_conversion'] = type_stats
        
        # Step 5: Validate cleaned data
        validation_results = validate_cleaned_data(df)
        cleaning_stats['validation'] = validation_results
        
        # Final statistics
        cleaning_stats['final_shape'] = [df.count(), len(df.columns)]
        cleaning_stats['cleaning_success'] = validation_results['validation_passed']
        
        # Save results
        save_cleaning_results(spark, df, cleaning_stats, args['output_path'])
        
        print("Data cleaning job completed successfully")
        
        job.commit()
        
    except Exception as e:
        print(f"Job failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()