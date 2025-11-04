"""
AWS Lambda function for data processing in ADPA pipeline.
"""

import json
import logging
import pandas as pd
import boto3
from io import StringIO, BytesIO
from typing import Dict, Any
import numpy as np

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda handler for data processing.
    
    Expected event structure:
    {
        "bucket": "bucket-name",
        "input_key": "path/to/input/file.csv",
        "output_key": "path/to/output/file.csv", 
        "processing_config": {
            "operation": "clean|profile|transform",
            "parameters": {...}
        }
    }
    """
    
    try:
        logger.info(f"Processing event: {json.dumps(event)}")
        
        # Extract event parameters
        bucket = event['bucket']
        input_key = event['input_key']
        output_key = event['output_key']
        processing_config = event.get('processing_config', {})
        operation = processing_config.get('operation', 'profile')
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Download data from S3
        logger.info(f"Downloading data from s3://{bucket}/{input_key}")
        response = s3_client.get_object(Bucket=bucket, Key=input_key)
        
        # Read data based on file type
        if input_key.endswith('.csv'):
            data = pd.read_csv(response['Body'])
        elif input_key.endswith('.json'):
            data = pd.read_json(response['Body'])
        else:
            raise ValueError(f"Unsupported file format: {input_key}")
        
        logger.info(f"Loaded data: {data.shape[0]} rows, {data.shape[1]} columns")
        
        # Process data based on operation
        if operation == 'profile':
            result = profile_data(data)
        elif operation == 'clean':
            result = clean_data(data, processing_config.get('parameters', {}))
        elif operation == 'transform':
            result = transform_data(data, processing_config.get('parameters', {}))
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        # Upload processed data back to S3
        if 'processed_data' in result:
            processed_data = result['processed_data']
            csv_buffer = StringIO()
            processed_data.to_csv(csv_buffer, index=False)
            
            s3_client.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=csv_buffer.getvalue(),
                ContentType='text/csv'
            )
            
            logger.info(f"Uploaded processed data to s3://{bucket}/{output_key}")
        
        # Return processing results
        response_body = {
            'statusCode': 200,
            'operation': operation,
            'input_shape': list(data.shape),
            'output_key': output_key,
            'processing_results': result.get('metrics', {}),
            'execution_time_ms': context.get_remaining_time_in_millis()
        }
        
        logger.info(f"Processing completed successfully")
        return response_body
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'operation': event.get('processing_config', {}).get('operation', 'unknown')
        }


def profile_data(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a comprehensive data profile.
    
    Args:
        data: Input DataFrame
        
    Returns:
        Dictionary with profiling results
    """
    logger.info("Profiling data...")
    
    # Basic statistics
    numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
    
    profile = {
        'shape': list(data.shape),
        'columns': data.columns.tolist(),
        'dtypes': data.dtypes.astype(str).to_dict(),
        'numeric_columns': numeric_columns,
        'categorical_columns': categorical_columns,
        'missing_values': data.isnull().sum().to_dict(),
        'missing_percentage': (data.isnull().sum() / len(data) * 100).to_dict(),
        'memory_usage_mb': round(data.memory_usage(deep=True).sum() / 1024 / 1024, 2)
    }
    
    # Numeric column statistics
    if numeric_columns:
        numeric_stats = data[numeric_columns].describe().to_dict()
        profile['numeric_statistics'] = numeric_stats
    
    # Categorical column statistics
    if categorical_columns:
        categorical_stats = {}
        for col in categorical_columns:
            categorical_stats[col] = {
                'unique_count': data[col].nunique(),
                'top_values': data[col].value_counts().head(5).to_dict()
            }
        profile['categorical_statistics'] = categorical_stats
    
    # Data quality assessment
    total_cells = data.shape[0] * data.shape[1]
    missing_cells = data.isnull().sum().sum()
    quality_score = max(0, 1 - (missing_cells / total_cells))
    
    profile['data_quality'] = {
        'completeness_score': round(quality_score, 3),
        'total_missing_cells': int(missing_cells),
        'completeness_percentage': round(quality_score * 100, 1)
    }
    
    return {
        'metrics': profile,
        'operation': 'profile'
    }


def clean_data(data: pd.DataFrame, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean the dataset based on provided parameters.
    
    Args:
        data: Input DataFrame
        parameters: Cleaning parameters
        
    Returns:
        Dictionary with cleaned data and metrics
    """
    logger.info("Cleaning data...")
    
    cleaned_data = data.copy()
    cleaning_stats = {
        'initial_rows': len(cleaned_data),
        'initial_columns': len(cleaned_data.columns)
    }
    
    # Remove duplicates
    initial_rows = len(cleaned_data)
    cleaned_data = cleaned_data.drop_duplicates()
    duplicates_removed = initial_rows - len(cleaned_data)
    cleaning_stats['duplicates_removed'] = duplicates_removed
    
    # Handle missing values
    missing_strategy = parameters.get('missing_strategy', 'drop')
    if missing_strategy == 'drop':
        cleaned_data = cleaned_data.dropna()
    elif missing_strategy == 'fill_median':
        numeric_columns = cleaned_data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            cleaned_data[col].fillna(cleaned_data[col].median(), inplace=True)
    elif missing_strategy == 'fill_mode':
        categorical_columns = cleaned_data.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            mode_value = cleaned_data[col].mode()
            if not mode_value.empty:
                cleaned_data[col].fillna(mode_value.iloc[0], inplace=True)
    
    # Handle outliers (simple IQR method)
    if parameters.get('handle_outliers', False):
        numeric_columns = cleaned_data.select_dtypes(include=[np.number]).columns
        outliers_handled = 0
        
        for col in numeric_columns:
            Q1 = cleaned_data[col].quantile(0.25)
            Q3 = cleaned_data[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Cap outliers
            outliers_mask = ((cleaned_data[col] < lower_bound) | (cleaned_data[col] > upper_bound))
            outliers_handled += outliers_mask.sum()
            
            cleaned_data.loc[cleaned_data[col] < lower_bound, col] = lower_bound
            cleaned_data.loc[cleaned_data[col] > upper_bound, col] = upper_bound
        
        cleaning_stats['outliers_handled'] = outliers_handled
    
    cleaning_stats.update({
        'final_rows': len(cleaned_data),
        'final_columns': len(cleaned_data.columns),
        'rows_removed': cleaning_stats['initial_rows'] - len(cleaned_data),
        'data_quality_improvement': round((len(cleaned_data) / cleaning_stats['initial_rows']) * 100, 2)
    })
    
    return {
        'processed_data': cleaned_data,
        'metrics': cleaning_stats,
        'operation': 'clean'
    }


def transform_data(data: pd.DataFrame, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the dataset based on provided parameters.
    
    Args:
        data: Input DataFrame
        parameters: Transformation parameters
        
    Returns:
        Dictionary with transformed data and metrics
    """
    logger.info("Transforming data...")
    
    transformed_data = data.copy()
    transform_stats = {
        'initial_shape': list(data.shape),
        'transformations_applied': []
    }
    
    # Encoding categorical variables
    if parameters.get('encode_categorical', True):
        categorical_columns = transformed_data.select_dtypes(include=['object']).columns
        
        for col in categorical_columns:
            if transformed_data[col].nunique() <= 10:  # One-hot encode low cardinality
                dummies = pd.get_dummies(transformed_data[col], prefix=col)
                transformed_data = pd.concat([transformed_data, dummies], axis=1)
                transformed_data.drop(col, axis=1, inplace=True)
                transform_stats['transformations_applied'].append(f"One-hot encoded {col}")
            else:  # Label encode high cardinality
                transformed_data[col] = pd.Categorical(transformed_data[col]).codes
                transform_stats['transformations_applied'].append(f"Label encoded {col}")
    
    # Normalize numeric features
    if parameters.get('normalize_numeric', False):
        numeric_columns = transformed_data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            # Simple min-max normalization
            min_val = transformed_data[col].min()
            max_val = transformed_data[col].max()
            
            if max_val != min_val:
                transformed_data[col] = (transformed_data[col] - min_val) / (max_val - min_val)
                transform_stats['transformations_applied'].append(f"Normalized {col}")
    
    transform_stats.update({
        'final_shape': list(transformed_data.shape),
        'features_added': transformed_data.shape[1] - data.shape[1],
        'transformation_count': len(transform_stats['transformations_applied'])
    })
    
    return {
        'processed_data': transformed_data,
        'metrics': transform_stats,
        'operation': 'transform'
    }


# For local testing
if __name__ == "__main__":
    # Sample test event
    test_event = {
        "bucket": "adpa-data-bucket",
        "input_key": "datasets/sample.csv",
        "output_key": "processed/sample_cleaned.csv",
        "processing_config": {
            "operation": "clean",
            "parameters": {
                "missing_strategy": "fill_median",
                "handle_outliers": True
            }
        }
    }
    
    class MockContext:
        def get_remaining_time_in_millis(self):
            return 30000
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))