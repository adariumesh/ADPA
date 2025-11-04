"""
AWS Glue ETL Script for Feature Engineering
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
from pyspark.ml.feature import *
from pyspark.ml import Pipeline
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
        'transformation_config'
    ])
    
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    return glueContext, spark, job, args


def parse_transformation_config(config_str: str) -> dict:
    """Parse transformation configuration from string."""
    try:
        config = json.loads(config_str)
    except:
        # Default configuration
        config = {
            'encode_categorical': True,
            'normalize_numeric': True,
            'feature_selection': True,
            'create_polynomial_features': False,
            'handle_skewness': True,
            'create_interaction_features': False
        }
    
    return config


def encode_categorical_features(df: DataFrame, config: dict) -> tuple[DataFrame, dict]:
    """
    Encode categorical features using appropriate strategies.
    
    Args:
        df: Input DataFrame
        config: Transformation configuration
        
    Returns:
        Tuple of (transformed DataFrame, transformation statistics)
    """
    print("Encoding categorical features...")
    
    # Get categorical columns
    categorical_columns = [col_name for col_name, col_type in df.dtypes 
                          if col_type == 'string']
    
    if not categorical_columns:
        return df, {'categorical_columns_processed': 0, 'encoding_strategy': 'none'}
    
    transformed_df = df
    encoding_stats = {
        'categorical_columns_processed': len(categorical_columns),
        'columns_encoded': [],
        'encoding_strategies': {}
    }
    
    for col_name in categorical_columns:
        # Check cardinality to decide encoding strategy
        cardinality = df.select(col_name).distinct().count()
        
        if cardinality <= 10:  # Low cardinality - use one-hot encoding
            # One-hot encoding using Spark ML
            indexer = StringIndexer(inputCol=col_name, outputCol=f"{col_name}_indexed")
            encoder = OneHotEncoder(inputCol=f"{col_name}_indexed", outputCol=f"{col_name}_encoded")
            
            # Create pipeline for this column
            pipeline = Pipeline(stages=[indexer, encoder])
            model = pipeline.fit(transformed_df)
            transformed_df = model.transform(transformed_df)
            
            # Drop original and indexed columns, keep only encoded
            transformed_df = transformed_df.drop(col_name, f"{col_name}_indexed")
            
            encoding_stats['columns_encoded'].append(col_name)
            encoding_stats['encoding_strategies'][col_name] = f'onehot_{cardinality}_categories'
            
        elif cardinality <= 100:  # Medium cardinality - use label encoding
            indexer = StringIndexer(inputCol=col_name, outputCol=f"{col_name}_encoded")
            model = indexer.fit(transformed_df)
            transformed_df = model.transform(transformed_df)
            
            # Drop original column
            transformed_df = transformed_df.drop(col_name)
            
            encoding_stats['columns_encoded'].append(col_name)
            encoding_stats['encoding_strategies'][col_name] = f'label_{cardinality}_categories'
            
        else:  # High cardinality - use target encoding or frequency encoding
            # Frequency encoding (count of each category)
            freq_df = df.groupBy(col_name).count().withColumnRenamed('count', f'{col_name}_frequency')
            transformed_df = transformed_df.join(freq_df, col_name, 'left')
            
            # Drop original column
            transformed_df = transformed_df.drop(col_name)
            
            encoding_stats['columns_encoded'].append(col_name)
            encoding_stats['encoding_strategies'][col_name] = f'frequency_{cardinality}_categories'
    
    print(f"Encoded {len(encoding_stats['columns_encoded'])} categorical columns")
    
    return transformed_df, encoding_stats


def normalize_numeric_features(df: DataFrame, config: dict) -> tuple[DataFrame, dict]:
    """
    Normalize and scale numeric features.
    
    Args:
        df: Input DataFrame
        config: Transformation configuration
        
    Returns:
        Tuple of (transformed DataFrame, transformation statistics)
    """
    print("Normalizing numeric features...")
    
    # Get numeric columns
    numeric_columns = [col_name for col_name, col_type in df.dtypes 
                      if col_type in ['int', 'bigint', 'double', 'float', 'decimal']]
    
    if not numeric_columns:
        return df, {'numeric_columns_processed': 0, 'normalization_strategy': 'none'}
    
    transformed_df = df
    normalization_stats = {
        'numeric_columns_processed': len(numeric_columns),
        'columns_normalized': [],
        'normalization_strategies': {}
    }
    
    # Use StandardScaler for most numeric features
    for col_name in numeric_columns:
        try:
            # Create vector for scaling
            assembler = VectorAssembler(inputCols=[col_name], outputCol=f"{col_name}_vector")
            scaler = StandardScaler(inputCol=f"{col_name}_vector", outputCol=f"{col_name}_scaled")
            
            # Apply transformations
            vector_df = assembler.transform(transformed_df)
            scaler_model = scaler.fit(vector_df)
            scaled_df = scaler_model.transform(vector_df)
            
            # Extract scaled values back to regular column
            def extract_scaled_value(vector):
                return float(vector[0]) if vector else None
            
            extract_udf = udf(extract_scaled_value, DoubleType())
            transformed_df = scaled_df.withColumn(
                f"{col_name}_normalized", 
                extract_udf(col(f"{col_name}_scaled"))
            ).drop(col_name, f"{col_name}_vector", f"{col_name}_scaled")
            
            normalization_stats['columns_normalized'].append(col_name)
            normalization_stats['normalization_strategies'][col_name] = 'standard_scaler'
            
        except Exception as e:
            print(f"Failed to normalize column {col_name}: {str(e)}")
            # Keep original column if normalization fails
            continue
    
    print(f"Normalized {len(normalization_stats['columns_normalized'])} numeric columns")
    
    return transformed_df, normalization_stats


def handle_skewed_features(df: DataFrame, config: dict) -> tuple[DataFrame, dict]:
    """
    Handle skewed numeric features using transformations.
    
    Args:
        df: Input DataFrame
        config: Transformation configuration
        
    Returns:
        Tuple of (transformed DataFrame, transformation statistics)
    """
    print("Handling skewed features...")
    
    if not config.get('handle_skewness', False):
        return df, {'skewness_handling': 'disabled'}
    
    # Get numeric columns (normalized ones)
    numeric_columns = [col_name for col_name in df.columns 
                      if col_name.endswith('_normalized')]
    
    transformed_df = df
    skewness_stats = {
        'columns_processed': 0,
        'transformations_applied': []
    }
    
    for col_name in numeric_columns:
        try:
            # Calculate skewness
            skewness_value = df.select(skewness(col(col_name))).collect()[0][0]
            
            if abs(skewness_value) > 1.0:  # Significantly skewed
                if skewness_value > 1.0:  # Right-skewed
                    # Apply log transformation (add 1 to handle zeros/negatives)
                    transformed_df = transformed_df.withColumn(
                        f"{col_name}_log",
                        log1p(col(col_name) - min(col(col_name)).over(Window.partitionBy()) + 1)
                    )
                    
                    skewness_stats['transformations_applied'].append({
                        'column': col_name,
                        'transformation': 'log',
                        'original_skewness': skewness_value
                    })
                    
                elif skewness_value < -1.0:  # Left-skewed
                    # Apply square transformation
                    max_val = df.select(max(col(col_name))).collect()[0][0]
                    transformed_df = transformed_df.withColumn(
                        f"{col_name}_squared",
                        pow(max_val - col(col_name) + 1, 2)
                    )
                    
                    skewness_stats['transformations_applied'].append({
                        'column': col_name,
                        'transformation': 'square',
                        'original_skewness': skewness_value
                    })
                
                skewness_stats['columns_processed'] += 1
                
        except Exception as e:
            print(f"Failed to handle skewness for column {col_name}: {str(e)}")
            continue
    
    print(f"Applied skewness handling to {skewness_stats['columns_processed']} columns")
    
    return transformed_df, skewness_stats


def create_polynomial_features(df: DataFrame, config: dict) -> tuple[DataFrame, dict]:
    """
    Create polynomial features for numeric columns.
    
    Args:
        df: Input DataFrame
        config: Transformation configuration
        
    Returns:
        Tuple of (transformed DataFrame, transformation statistics)
    """
    print("Creating polynomial features...")
    
    if not config.get('create_polynomial_features', False):
        return df, {'polynomial_features': 'disabled'}
    
    # Get numeric columns (normalized ones)
    numeric_columns = [col_name for col_name in df.columns 
                      if col_name.endswith('_normalized')]
    
    # Limit to first 5 columns to avoid feature explosion
    selected_columns = numeric_columns[:5]
    
    transformed_df = df
    poly_stats = {
        'columns_processed': len(selected_columns),
        'polynomial_features_created': []
    }
    
    # Create squared features
    for col_name in selected_columns:
        try:
            transformed_df = transformed_df.withColumn(
                f"{col_name}_squared",
                pow(col(col_name), 2)
            )
            
            poly_stats['polynomial_features_created'].append(f"{col_name}_squared")
            
        except Exception as e:
            print(f"Failed to create polynomial feature for {col_name}: {str(e)}")
            continue
    
    # Create interaction features (limited to avoid explosion)
    if len(selected_columns) >= 2:
        for i in range(min(3, len(selected_columns))):
            for j in range(i + 1, min(3, len(selected_columns))):
                try:
                    col1, col2 = selected_columns[i], selected_columns[j]
                    interaction_name = f"{col1}_{col2}_interaction"
                    
                    transformed_df = transformed_df.withColumn(
                        interaction_name,
                        col(col1) * col(col2)
                    )
                    
                    poly_stats['polynomial_features_created'].append(interaction_name)
                    
                except Exception as e:
                    print(f"Failed to create interaction feature: {str(e)}")
                    continue
    
    print(f"Created {len(poly_stats['polynomial_features_created'])} polynomial features")
    
    return transformed_df, poly_stats


def perform_feature_selection(df: DataFrame, config: dict) -> tuple[DataFrame, dict]:
    """
    Perform feature selection to reduce dimensionality.
    
    Args:
        df: Input DataFrame
        config: Transformation configuration
        
    Returns:
        Tuple of (transformed DataFrame, selection statistics)
    """
    print("Performing feature selection...")
    
    if not config.get('feature_selection', False):
        return df, {'feature_selection': 'disabled'}
    
    initial_columns = len(df.columns)
    
    # Remove columns with too many nulls
    threshold = 0.5  # 50% null threshold
    columns_to_keep = []
    
    for col_name in df.columns:
        null_ratio = df.filter(col(col_name).isNull()).count() / df.count()
        if null_ratio < threshold:
            columns_to_keep.append(col_name)
    
    transformed_df = df.select(columns_to_keep)
    
    # Remove highly correlated features (simplified)
    # In practice, you'd use correlation matrix and remove one from each highly correlated pair
    
    selection_stats = {
        'initial_features': initial_columns,
        'final_features': len(columns_to_keep),
        'features_removed': initial_columns - len(columns_to_keep),
        'removal_reason': 'high_null_ratio'
    }
    
    print(f"Feature selection: {initial_columns} -> {len(columns_to_keep)} features")
    
    return transformed_df, selection_stats


def validate_transformed_data(df: DataFrame) -> dict:
    """
    Validate the transformed dataset.
    
    Args:
        df: Transformed DataFrame
        
    Returns:
        Validation results
    """
    print("Validating transformed data...")
    
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
    
    # Identify feature types
    numeric_features = [col_name for col_name, col_type in df.dtypes 
                       if col_type in ['int', 'bigint', 'double', 'float']]
    vector_features = [col_name for col_name in df.columns if 'encoded' in col_name]
    
    validation = {
        'row_count': row_count,
        'column_count': column_count,
        'total_missing_values': total_missing,
        'completeness_score': 1 - (total_missing / (row_count * column_count)) if row_count * column_count > 0 else 0,
        'numeric_features': len(numeric_features),
        'encoded_features': len(vector_features),
        'data_types': data_types,
        'ml_ready': total_missing == 0 and len(numeric_features) > 0
    }
    
    print(f"Validation completed. ML ready: {validation['ml_ready']}")
    
    return validation


def save_transformation_results(spark, df: DataFrame, stats: dict, output_path: str):
    """
    Save transformed data and statistics.
    
    Args:
        spark: Spark session
        df: Transformed DataFrame
        stats: Transformation statistics
        output_path: Output path
    """
    print(f"Saving transformed data to: {output_path}")
    
    # Save transformed data
    df.coalesce(10).write.mode('overwrite').option('header', 'true').csv(f"{output_path}/data")
    
    # Save transformation statistics
    stats_json = json.dumps(stats, indent=2, default=str)
    stats_df = spark.createDataFrame([(stats_json,)], ['transformation_stats'])
    stats_df.coalesce(1).write.mode('overwrite').text(f"{output_path}/stats")
    
    # Save feature metadata for ML pipeline
    feature_metadata = {
        'total_features': len(df.columns),
        'feature_names': df.columns,
        'feature_types': dict(df.dtypes),
        'ml_ready': stats.get('validation', {}).get('ml_ready', False)
    }
    
    metadata_json = json.dumps(feature_metadata, indent=2)
    metadata_df = spark.createDataFrame([(metadata_json,)], ['feature_metadata'])
    metadata_df.coalesce(1).write.mode('overwrite').text(f"{output_path}/metadata")
    
    print("Transformed data and metadata saved successfully")


def main():
    """Main ETL execution."""
    try:
        # Initialize Glue context
        glueContext, spark, job, args = create_glue_context()
        
        print(f"Starting feature engineering job: {args['JOB_NAME']}")
        print(f"Input path: {args['input_path']}")
        print(f"Output path: {args['output_path']}")
        
        # Parse transformation configuration
        config = parse_transformation_config(args.get('transformation_config', '{}'))
        print(f"Transformation configuration: {config}")
        
        # Read input data (cleaned data from previous step)
        df = spark.read.option("header", "true").option("inferSchema", "true").csv(args['input_path'])
        
        print(f"Data loaded successfully: {df.count()} rows, {len(df.columns)} columns")
        
        # Initialize transformation statistics
        transformation_stats = {
            'initial_shape': [df.count(), len(df.columns)],
            'transformation_config': config,
            'transformations': {}
        }
        
        # Step 1: Encode categorical features
        if config.get('encode_categorical', True):
            df, encoding_stats = encode_categorical_features(df, config)
            transformation_stats['transformations']['categorical_encoding'] = encoding_stats
        
        # Step 2: Normalize numeric features
        if config.get('normalize_numeric', True):
            df, normalization_stats = normalize_numeric_features(df, config)
            transformation_stats['transformations']['numeric_normalization'] = normalization_stats
        
        # Step 3: Handle skewed features
        if config.get('handle_skewness', True):
            df, skewness_stats = handle_skewed_features(df, config)
            transformation_stats['transformations']['skewness_handling'] = skewness_stats
        
        # Step 4: Create polynomial features
        if config.get('create_polynomial_features', False):
            df, poly_stats = create_polynomial_features(df, config)
            transformation_stats['transformations']['polynomial_features'] = poly_stats
        
        # Step 5: Feature selection
        if config.get('feature_selection', True):
            df, selection_stats = perform_feature_selection(df, config)
            transformation_stats['transformations']['feature_selection'] = selection_stats
        
        # Step 6: Validate transformed data
        validation_results = validate_transformed_data(df)
        transformation_stats['validation'] = validation_results
        
        # Final statistics
        transformation_stats['final_shape'] = [df.count(), len(df.columns)]
        transformation_stats['transformation_success'] = validation_results['ml_ready']
        
        # Save results
        save_transformation_results(spark, df, transformation_stats, args['output_path'])
        
        print("Feature engineering job completed successfully")
        
        job.commit()
        
    except Exception as e:
        print(f"Job failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()