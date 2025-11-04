"""
Data cleaning pipeline step.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from ...agent.core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus


class DataCleaningStep(PipelineStep):
    """
    Pipeline step for data cleaning and preprocessing.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.CLEANING, "data_cleaning")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute data cleaning step.
        
        Args:
            data: Input dataset
            config: Step configuration
            context: Execution context
            
        Returns:
            ExecutionResult with cleaned data
        """
        if data is None:
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=["No data provided for cleaning"]
            )
        
        try:
            self.logger.info("Starting data cleaning...")
            
            cleaned_data = data.copy()
            cleaning_stats = {
                "initial_rows": len(cleaned_data),
                "initial_columns": len(cleaned_data.columns),
                "initial_missing_values": cleaned_data.isnull().sum().sum()
            }
            
            # 1. Remove duplicates
            initial_rows = len(cleaned_data)
            cleaned_data = cleaned_data.drop_duplicates()
            duplicates_removed = initial_rows - len(cleaned_data)
            cleaning_stats["duplicates_removed"] = duplicates_removed
            
            # 2. Handle missing values
            missing_strategy = self.config.get("missing_value_strategy", "impute")
            missing_handled = self._handle_missing_values(cleaned_data, missing_strategy)
            cleaning_stats.update(missing_handled)
            
            # 3. Handle outliers (if configured)
            if self.config.get("outlier_detection", False):
                outlier_stats = self._handle_outliers(cleaned_data)
                cleaning_stats.update(outlier_stats)
            
            # 4. Data type conversion
            if self.config.get("data_type_conversion", True):
                conversion_stats = self._convert_data_types(cleaned_data)
                cleaning_stats.update(conversion_stats)
            
            # 5. Final validation
            final_missing = cleaned_data.isnull().sum().sum()
            cleaning_stats["final_missing_values"] = final_missing
            cleaning_stats["final_rows"] = len(cleaned_data)
            cleaning_stats["final_columns"] = len(cleaned_data.columns)
            
            self.logger.info(f"Data cleaning completed. Rows: {cleaning_stats['initial_rows']} -> {cleaning_stats['final_rows']}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=cleaned_data,
                metrics=cleaning_stats,
                artifacts={
                    "cleaning_report": self._generate_cleaning_report(cleaning_stats),
                    "data_quality_score": self._calculate_quality_score(cleaning_stats)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Data cleaning failed: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Data cleaning error: {str(e)}"]
            )
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate inputs for data cleaning step.
        
        Args:
            data: Input dataset
            config: Step configuration
            
        Returns:
            True if inputs are valid
        """
        if data is None or data.empty:
            self.logger.error("Data cleaning validation failed: no data provided")
            return False
        
        return True
    
    def _handle_missing_values(self, data: pd.DataFrame, strategy: str) -> Dict[str, Any]:
        """Handle missing values in the dataset."""
        initial_missing = data.isnull().sum().sum()
        
        if strategy == "drop":
            # Drop rows with any missing values
            data.dropna(inplace=True)
        elif strategy == "impute":
            # Simple imputation
            for column in data.columns:
                if data[column].isnull().sum() > 0:
                    if data[column].dtype in ['int64', 'float64']:
                        # Use median for numeric columns
                        data[column].fillna(data[column].median(), inplace=True)
                    else:
                        # Use mode for categorical columns
                        mode_value = data[column].mode()
                        if not mode_value.empty:
                            data[column].fillna(mode_value.iloc[0], inplace=True)
        elif strategy == "advanced_impute":
            # More sophisticated imputation could be implemented here
            # For now, use forward fill + backward fill
            data.fillna(method='ffill', inplace=True)
            data.fillna(method='bfill', inplace=True)
        
        final_missing = data.isnull().sum().sum()
        
        return {
            "missing_values_handled": initial_missing - final_missing,
            "missing_value_strategy": strategy
        }
    
    def _handle_outliers(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Handle outliers in numeric columns."""
        outliers_handled = 0
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = ((data[column] < lower_bound) | (data[column] > upper_bound))
            outliers_count = outliers.sum()
            
            if outliers_count > 0:
                # Cap outliers instead of removing them
                data.loc[data[column] < lower_bound, column] = lower_bound
                data.loc[data[column] > upper_bound, column] = upper_bound
                outliers_handled += outliers_count
        
        return {
            "outliers_handled": outliers_handled,
            "outlier_method": "IQR_capping"
        }
    
    def _convert_data_types(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Convert data types for optimization."""
        conversions = 0
        
        for column in data.columns:
            original_dtype = data[column].dtype
            
            # Convert object columns that look like numbers
            if data[column].dtype == 'object':
                try:
                    # Try to convert to numeric
                    converted = pd.to_numeric(data[column], errors='coerce')
                    if not converted.isnull().all():
                        data[column] = converted
                        conversions += 1
                except:
                    pass
            
            # Optimize integer columns
            elif data[column].dtype in ['int64']:
                try:
                    data[column] = pd.to_numeric(data[column], downcast='integer')
                    if data[column].dtype != original_dtype:
                        conversions += 1
                except:
                    pass
            
            # Optimize float columns
            elif data[column].dtype in ['float64']:
                try:
                    data[column] = pd.to_numeric(data[column], downcast='float')
                    if data[column].dtype != original_dtype:
                        conversions += 1
                except:
                    pass
        
        return {
            "data_type_conversions": conversions
        }
    
    def _generate_cleaning_report(self, stats: Dict[str, Any]) -> str:
        """Generate a human-readable cleaning report."""
        report = f"""
Data Cleaning Report:
- Initial dataset: {stats['initial_rows']} rows, {stats['initial_columns']} columns
- Final dataset: {stats['final_rows']} rows, {stats['final_columns']} columns
- Duplicates removed: {stats.get('duplicates_removed', 0)}
- Missing values handled: {stats.get('missing_values_handled', 0)}
- Outliers handled: {stats.get('outliers_handled', 0)}
- Data type conversions: {stats.get('data_type_conversions', 0)}
- Final missing values: {stats['final_missing_values']}
"""
        return report.strip()
    
    def _calculate_quality_score(self, stats: Dict[str, Any]) -> float:
        """Calculate a data quality score (0-1)."""
        # Simple quality score based on completeness and consistency
        total_cells = stats['final_rows'] * stats['final_columns']
        missing_ratio = stats['final_missing_values'] / total_cells if total_cells > 0 else 0
        
        # Quality score: 1 - missing_ratio (simplified)
        quality_score = max(0, 1 - missing_ratio)
        
        return round(quality_score, 3)