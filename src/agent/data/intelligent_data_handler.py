"""
Intelligent Data Handler - Unified data processing with LLM-powered reasoning.
Replaces redundant data loaders with single intelligent component.
"""

import logging
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler, LabelEncoder
from sklearn.impute import SimpleImputer, KNNImputer
import warnings
warnings.filterwarnings('ignore')

from ..core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus, DatasetInfo
from ..utils.llm_integration import LLMReasoningEngine, ReasoningContext, AgenticReasoningMixin


class IntelligentDataHandler(PipelineStep, AgenticReasoningMixin):
    """
    Unified intelligent data handler that combines loading, profiling, and preprocessing.
    
    Replaces multiple redundant data loaders with single component that:
    - Intelligently loads data from various sources
    - Performs LLM-guided data quality assessment
    - Applies adaptive preprocessing strategies
    - Provides comprehensive data profiling
    - Optimizes data for downstream ML tasks
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.INGESTION, "intelligent_data_handler")
        AgenticReasoningMixin.__init__(self)
        
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize reasoning engine
        self.reasoning_engine = LLMReasoningEngine()
        
        # Data processing strategies
        self.preprocessing_strategies = {
            "missing_values": ["drop", "simple_impute", "knn_impute", "iterative_impute"],
            "categorical_encoding": ["label", "onehot", "target", "frequency"],
            "scaling": ["standard", "robust", "minmax", "none"],
            "outlier_handling": ["remove", "cap", "transform", "none"]
        }
        
        # Cache and storage
        self.cache_dir = Path(self.config.get("cache_dir", "./data/cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Intelligent Data Handler initialized")
    
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute intelligent data handling with LLM-guided processing.
        
        Args:
            data: Input data (optional if loading from source)
            config: Processing configuration
            context: Execution context with objective information
            
        Returns:
            ExecutionResult with processed data and intelligence insights
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting intelligent data handling...")
            
            # Merge configuration
            processing_config = {**self.config, **(config or {})}
            
            # Step 1: Load or validate data
            if data is None:
                loaded_data = self._intelligent_data_loading(processing_config, context)
            else:
                loaded_data = data.copy()
                self.logger.info(f"Using provided data: {loaded_data.shape}")
            
            # Step 2: Intelligent data profiling and assessment
            data_profile = self._intelligent_data_profiling(loaded_data, context)
            
            # Step 3: LLM-guided preprocessing strategy
            preprocessing_strategy = self._determine_preprocessing_strategy(
                loaded_data, data_profile, context
            )
            
            # Step 4: Apply intelligent preprocessing
            processed_data = self._apply_intelligent_preprocessing(
                loaded_data, preprocessing_strategy, data_profile
            )
            
            # Step 5: Final quality assessment
            final_assessment = self._assess_processed_data_quality(
                processed_data, data_profile, preprocessing_strategy
            )
            
            # Calculate processing metrics
            processing_time = time.time() - start_time
            
            self.logger.info(f"Intelligent data handling completed in {processing_time:.2f}s")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=processed_data,
                metrics={
                    "original_shape": loaded_data.shape,
                    "processed_shape": processed_data.shape,
                    "processing_time_seconds": processing_time,
                    "data_quality_score": final_assessment["quality_score"],
                    "improvements_applied": len(preprocessing_strategy["steps"]),
                    "memory_usage_mb": processed_data.memory_usage(deep=True).sum() / 1024 / 1024
                },
                artifacts={
                    "data_profile": data_profile,
                    "preprocessing_strategy": preprocessing_strategy,
                    "quality_assessment": final_assessment,
                    "intelligence_insights": self._generate_intelligence_insights(
                        data_profile, preprocessing_strategy, final_assessment
                    )
                },
                step_output={
                    "data_ready": True,
                    "preprocessing_success": True,
                    "quality_improved": final_assessment["quality_score"] > data_profile["initial_quality_score"],
                    "recommended_next_steps": final_assessment["recommendations"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Intelligent data handling failed: {e}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Data handling error: {str(e)}"],
                metrics={"processing_time_seconds": time.time() - start_time}
            )
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate inputs for intelligent data handling.
        
        Args:
            data: Input data
            config: Configuration
            
        Returns:
            True if inputs are valid
        """
        # If data is provided, validate it
        if data is not None:
            if len(data) == 0:
                self.logger.error("Provided data is empty")
                return False
            return True
        
        # If no data, check if source path is provided
        if config and "source_path" in config:
            source_path = config["source_path"]
            if os.path.exists(source_path):
                return True
            else:
                self.logger.error(f"Source file does not exist: {source_path}")
                return False
        
        self.logger.error("No data or valid source path provided")
        return False
    
    def _intelligent_data_loading(self, 
                                config: Dict[str, Any],
                                context: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """
        Intelligently load data from various sources with adaptive strategies.
        
        Args:
            config: Loading configuration
            context: Execution context
            
        Returns:
            Loaded DataFrame
        """
        source_path = config.get("source_path")
        if not source_path:
            raise ValueError("No source path provided for data loading")
        
        self.logger.info(f"Intelligently loading data from: {source_path}")
        
        # Check cache first
        if config.get("use_cache", True):
            cached_data = self._try_load_from_cache(source_path)
            if cached_data is not None:
                self.logger.info("Loaded data from cache")
                return cached_data
        
        # Determine file format and optimal loading strategy
        loading_strategy = self._determine_loading_strategy(source_path, config)
        
        # Load data with intelligent parameters
        try:
            if source_path.endswith('.csv'):
                data = self._intelligent_csv_loading(source_path, loading_strategy)
            elif source_path.endswith('.json'):
                data = pd.read_json(source_path, **loading_strategy.get('json_params', {}))
            elif source_path.endswith('.parquet'):
                data = pd.read_parquet(source_path, **loading_strategy.get('parquet_params', {}))
            elif source_path.endswith(('.xlsx', '.xls')):
                data = pd.read_excel(source_path, **loading_strategy.get('excel_params', {}))
            else:
                raise ValueError(f"Unsupported file format: {source_path}")
            
            # Cache the loaded data
            if config.get("use_cache", True):
                self._cache_data(source_path, data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise
    
    def _determine_loading_strategy(self, 
                                  source_path: str,
                                  config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM reasoning to determine optimal loading strategy.
        
        Args:
            source_path: Path to data file
            config: Loading configuration
            
        Returns:
            Dictionary with loading strategy
        """
        file_size_mb = os.path.getsize(source_path) / 1024 / 1024
        file_ext = Path(source_path).suffix.lower()
        
        strategy_prompt = f"""
        Determine optimal data loading strategy:
        
        File: {source_path}
        Size: {file_size_mb:.1f} MB
        Format: {file_ext}
        Available Memory: {self._estimate_available_memory()} MB
        
        Recommend optimal loading parameters for:
        1. Memory efficiency
        2. Loading speed
        3. Data integrity
        
        Consider chunk loading for large files, dtype optimization, and error handling.
        """
        
        strategy_response = self.reasoning_engine._call_llm(strategy_prompt, max_tokens=600)
        
        # Extract strategy (simplified implementation)
        strategy = {
            "use_chunks": file_size_mb > 500,
            "chunk_size": min(10000, max(1000, int(100000 / max(1, file_size_mb)))),
            "optimize_dtypes": True,
            "handle_errors": "coerce"
        }
        
        if file_ext == '.csv':
            strategy['csv_params'] = {
                "low_memory": file_size_mb > 100,
                "dtype": str if file_size_mb > 200 else None,  # Let pandas infer for smaller files
                "na_values": ['', 'NULL', 'null', 'N/A', 'n/a', 'NA', 'missing'],
                "encoding": 'utf-8'
            }
        
        return strategy
    
    def _intelligent_csv_loading(self, 
                               source_path: str,
                               strategy: Dict[str, Any]) -> pd.DataFrame:
        """
        Intelligently load CSV with adaptive parameters.
        
        Args:
            source_path: Path to CSV file
            strategy: Loading strategy
            
        Returns:
            Loaded DataFrame
        """
        csv_params = strategy.get('csv_params', {})
        
        if strategy.get('use_chunks', False):
            # Load in chunks for large files
            chunks = []
            chunk_size = strategy.get('chunk_size', 10000)
            
            for chunk in pd.read_csv(source_path, chunksize=chunk_size, **csv_params):
                chunks.append(chunk)
                if len(chunks) > 100:  # Limit memory usage
                    break
            
            data = pd.concat(chunks, ignore_index=True)
        else:
            # Load entire file
            data = pd.read_csv(source_path, **csv_params)
        
        # Optimize dtypes if requested
        if strategy.get('optimize_dtypes', True):
            data = self._optimize_dtypes(data)
        
        return data
    
    def _optimize_dtypes(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize data types for memory efficiency.
        
        Args:
            data: DataFrame to optimize
            
        Returns:
            DataFrame with optimized dtypes
        """
        optimized_data = data.copy()
        
        for col in optimized_data.columns:
            col_type = optimized_data[col].dtype
            
            if col_type == 'object':
                # Try to convert to numeric
                try:
                    numeric_series = pd.to_numeric(optimized_data[col], errors='coerce')
                    if not numeric_series.isnull().all():
                        optimized_data[col] = numeric_series
                        continue
                except:
                    pass
                
                # Check if it's a categorical with few unique values
                unique_ratio = optimized_data[col].nunique() / len(optimized_data[col])
                if unique_ratio < 0.1:  # Less than 10% unique values
                    optimized_data[col] = optimized_data[col].astype('category')
            
            elif col_type in ['int64', 'float64']:
                # Downcast numeric types
                if col_type == 'int64':
                    optimized_data[col] = pd.to_numeric(optimized_data[col], downcast='integer')
                else:
                    optimized_data[col] = pd.to_numeric(optimized_data[col], downcast='float')
        
        return optimized_data
    
    def _intelligent_data_profiling(self, 
                                  data: pd.DataFrame,
                                  context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform intelligent data profiling with LLM insights.
        
        Args:
            data: DataFrame to profile
            context: Execution context
            
        Returns:
            Comprehensive data profile
        """
        self.logger.info("Performing intelligent data profiling...")
        
        # Basic profiling
        basic_profile = {
            "shape": data.shape,
            "columns": list(data.columns),
            "dtypes": data.dtypes.asdict() if hasattr(data.dtypes, 'asdict') else data.dtypes.to_dict(),
            "missing_values": data.isnull().sum().to_dict(),
            "memory_usage_mb": data.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
        # Advanced profiling
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        
        advanced_profile = {
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "unique_counts": {col: data[col].nunique() for col in data.columns},
            "duplicate_rows": data.duplicated().sum(),
            "missing_ratio": data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        }
        
        # Statistical summary for numeric columns
        if numeric_columns:
            numeric_summary = data[numeric_columns].describe().to_dict()
            advanced_profile["numeric_summary"] = numeric_summary
        
        # LLM-powered insights
        profiling_insights = self._generate_profiling_insights(data, basic_profile, advanced_profile, context)
        
        # Quality assessment
        quality_score = self._calculate_data_quality_score(basic_profile, advanced_profile)
        
        return {
            **basic_profile,
            **advanced_profile,
            "initial_quality_score": quality_score,
            "profiling_insights": profiling_insights,
            "profiling_timestamp": datetime.now().isoformat()
        }
    
    def _generate_profiling_insights(self, 
                                   data: pd.DataFrame,
                                   basic_profile: Dict[str, Any],
                                   advanced_profile: Dict[str, Any],
                                   context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate LLM-powered insights about the data.
        
        Args:
            data: DataFrame being profiled
            basic_profile: Basic profiling information
            advanced_profile: Advanced profiling information
            context: Execution context
            
        Returns:
            Dictionary with intelligent insights
        """
        objective = context.get("objective", "unknown") if context else "unknown"
        
        insights_prompt = f"""
        Analyze this dataset and provide intelligent insights:
        
        Dataset Shape: {basic_profile['shape']}
        Missing Data Ratio: {advanced_profile['missing_ratio']:.3f}
        Numeric Columns: {len(advanced_profile['numeric_columns'])}
        Categorical Columns: {len(advanced_profile['categorical_columns'])}
        Duplicate Rows: {advanced_profile['duplicate_rows']}
        
        ML Objective: {objective}
        
        Provide insights about:
        1. Data quality issues
        2. Preprocessing recommendations
        3. Potential ML challenges
        4. Feature engineering opportunities
        5. Model suitability
        
        Be specific and actionable.
        """
        
        insights_response = self.reasoning_engine._call_llm(insights_prompt, max_tokens=800)
        
        return {
            "llm_insights": insights_response,
            "quality_issues": self._identify_quality_issues(basic_profile, advanced_profile),
            "preprocessing_needs": self._identify_preprocessing_needs(data, advanced_profile),
            "feature_opportunities": self._identify_feature_opportunities(advanced_profile)
        }
    
    def _determine_preprocessing_strategy(self, 
                                        data: pd.DataFrame,
                                        data_profile: Dict[str, Any],
                                        context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use LLM reasoning to determine optimal preprocessing strategy.
        
        Args:
            data: Input DataFrame
            data_profile: Data profiling results
            context: Execution context
            
        Returns:
            Dictionary with preprocessing strategy
        """
        reasoning_context = ReasoningContext(
            domain="data_preprocessing",
            objective=context.get("objective", "unknown") if context else "unknown",
            data_context={
                "data_profile": data_profile,
                "profiling_insights": data_profile.get("profiling_insights", {}),
                "quality_score": data_profile.get("initial_quality_score", 0.5)
            }
        )
        
        strategy_response = self.reasoning_engine.reason_about_data_strategy(reasoning_context)
        
        # Extract specific preprocessing steps
        preprocessing_steps = self._extract_preprocessing_steps(data_profile, strategy_response)
        
        return {
            "reasoning": strategy_response.reasoning,
            "confidence": strategy_response.confidence,
            "steps": preprocessing_steps,
            "strategy_type": "intelligent_adaptive",
            "estimated_improvement": self._estimate_quality_improvement(preprocessing_steps),
            "alternatives": strategy_response.alternatives
        }
    
    def _extract_preprocessing_steps(self, 
                                   data_profile: Dict[str, Any],
                                   strategy_response) -> List[Dict[str, Any]]:
        """
        Extract specific preprocessing steps from LLM strategy response.
        
        Args:
            data_profile: Data profiling results
            strategy_response: LLM strategy response
            
        Returns:
            List of preprocessing steps
        """
        steps = []
        
        # Missing value handling
        if data_profile.get("missing_ratio", 0) > 0.01:  # More than 1% missing
            missing_strategy = self._determine_missing_value_strategy(data_profile)
            steps.append({
                "step": "missing_value_handling",
                "strategy": missing_strategy,
                "priority": "high",
                "reason": f"Dataset has {data_profile.get('missing_ratio', 0):.1%} missing values"
            })
        
        # Categorical encoding
        if len(data_profile.get("categorical_columns", [])) > 0:
            encoding_strategy = self._determine_encoding_strategy(data_profile)
            steps.append({
                "step": "categorical_encoding",
                "strategy": encoding_strategy,
                "priority": "high",
                "reason": f"Dataset has {len(data_profile.get('categorical_columns', []))} categorical columns"
            })
        
        # Feature scaling
        if len(data_profile.get("numeric_columns", [])) > 1:
            scaling_strategy = self._determine_scaling_strategy(data_profile)
            steps.append({
                "step": "feature_scaling",
                "strategy": scaling_strategy,
                "priority": "medium",
                "reason": "Multiple numeric features need scaling"
            })
        
        # Outlier handling
        outlier_severity = self._assess_outlier_severity(data_profile)
        if outlier_severity > 0.1:  # Significant outliers
            steps.append({
                "step": "outlier_handling",
                "strategy": "robust_methods",
                "priority": "medium",
                "reason": f"Significant outliers detected (severity: {outlier_severity:.2f})"
            })
        
        # Duplicate removal
        if data_profile.get("duplicate_rows", 0) > 0:
            steps.append({
                "step": "duplicate_removal",
                "strategy": "remove_duplicates",
                "priority": "low",
                "reason": f"{data_profile.get('duplicate_rows', 0)} duplicate rows found"
            })
        
        return steps
    
    def _apply_intelligent_preprocessing(self, 
                                       data: pd.DataFrame,
                                       strategy: Dict[str, Any],
                                       data_profile: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply intelligent preprocessing based on strategy.
        
        Args:
            data: Input DataFrame
            strategy: Preprocessing strategy
            data_profile: Data profiling results
            
        Returns:
            Preprocessed DataFrame
        """
        processed_data = data.copy()
        applied_steps = []
        
        for step in strategy.get("steps", []):
            try:
                step_name = step["step"]
                step_strategy = step["strategy"]
                
                self.logger.info(f"Applying {step_name} with strategy: {step_strategy}")
                
                if step_name == "missing_value_handling":
                    processed_data = self._handle_missing_values(processed_data, step_strategy, data_profile)
                elif step_name == "categorical_encoding":
                    processed_data = self._encode_categorical_features(processed_data, step_strategy, data_profile)
                elif step_name == "feature_scaling":
                    processed_data = self._scale_features(processed_data, step_strategy, data_profile)
                elif step_name == "outlier_handling":
                    processed_data = self._handle_outliers(processed_data, step_strategy, data_profile)
                elif step_name == "duplicate_removal":
                    processed_data = self._remove_duplicates(processed_data)
                
                applied_steps.append(step_name)
                
            except Exception as e:
                self.logger.warning(f"Failed to apply {step_name}: {e}")
                continue
        
        self.logger.info(f"Applied {len(applied_steps)} preprocessing steps: {applied_steps}")
        return processed_data
    
    def _handle_missing_values(self, 
                             data: pd.DataFrame,
                             strategy: str,
                             data_profile: Dict[str, Any]) -> pd.DataFrame:
        """Handle missing values with intelligent strategy."""
        if strategy == "simple_impute":
            numeric_columns = data_profile.get("numeric_columns", [])
            categorical_columns = data_profile.get("categorical_columns", [])
            
            # Impute numeric columns with median
            if numeric_columns:
                imputer = SimpleImputer(strategy='median')
                data[numeric_columns] = imputer.fit_transform(data[numeric_columns])
            
            # Impute categorical columns with mode
            if categorical_columns:
                for col in categorical_columns:
                    if data[col].isnull().sum() > 0:
                        mode_value = data[col].mode().iloc[0] if len(data[col].mode()) > 0 else "Unknown"
                        data[col].fillna(mode_value, inplace=True)
        
        elif strategy == "knn_impute":
            numeric_columns = data_profile.get("numeric_columns", [])
            if numeric_columns:
                imputer = KNNImputer(n_neighbors=5)
                data[numeric_columns] = imputer.fit_transform(data[numeric_columns])
        
        elif strategy == "drop":
            # Drop rows with missing values
            data = data.dropna()
        
        return data
    
    def _encode_categorical_features(self, 
                                   data: pd.DataFrame,
                                   strategy: str,
                                   data_profile: Dict[str, Any]) -> pd.DataFrame:
        """Encode categorical features with intelligent strategy."""
        categorical_columns = data_profile.get("categorical_columns", [])
        
        if not categorical_columns:
            return data
        
        if strategy == "label_encoding":
            for col in categorical_columns:
                le = LabelEncoder()
                data[col] = le.fit_transform(data[col].astype(str))
        
        elif strategy == "onehot_encoding":
            # One-hot encode with reasonable limits
            for col in categorical_columns:
                if data[col].nunique() <= 10:  # Only for low cardinality
                    dummies = pd.get_dummies(data[col], prefix=col)
                    data = pd.concat([data.drop(col, axis=1), dummies], axis=1)
        
        return data
    
    def _scale_features(self, 
                       data: pd.DataFrame,
                       strategy: str,
                       data_profile: Dict[str, Any]) -> pd.DataFrame:
        """Scale features with intelligent strategy."""
        numeric_columns = data_profile.get("numeric_columns", [])
        
        if not numeric_columns:
            return data
        
        if strategy == "standard_scaling":
            scaler = StandardScaler()
            data[numeric_columns] = scaler.fit_transform(data[numeric_columns])
        elif strategy == "robust_scaling":
            scaler = RobustScaler()
            data[numeric_columns] = scaler.fit_transform(data[numeric_columns])
        
        return data
    
    def _handle_outliers(self, 
                        data: pd.DataFrame,
                        strategy: str,
                        data_profile: Dict[str, Any]) -> pd.DataFrame:
        """Handle outliers with intelligent strategy."""
        numeric_columns = data_profile.get("numeric_columns", [])
        
        if strategy == "remove_outliers":
            for col in numeric_columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                data = data[(data[col] >= lower_bound) & (data[col] <= upper_bound)]
        
        return data
    
    def _remove_duplicates(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows."""
        return data.drop_duplicates()
    
    def _calculate_data_quality_score(self, 
                                    basic_profile: Dict[str, Any],
                                    advanced_profile: Dict[str, Any]) -> float:
        """Calculate overall data quality score."""
        score = 1.0
        
        # Penalty for missing data
        missing_penalty = min(0.3, advanced_profile.get("missing_ratio", 0) * 2)
        score -= missing_penalty
        
        # Penalty for duplicates
        if basic_profile.get("shape", [0])[0] > 0:
            duplicate_ratio = advanced_profile.get("duplicate_rows", 0) / basic_profile["shape"][0]
            duplicate_penalty = min(0.2, duplicate_ratio)
            score -= duplicate_penalty
        
        # Penalty for too few samples
        if basic_profile.get("shape", [0])[0] < 100:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _assess_processed_data_quality(self, 
                                     processed_data: pd.DataFrame,
                                     original_profile: Dict[str, Any],
                                     strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality of processed data."""
        # Recalculate quality metrics
        new_missing_ratio = processed_data.isnull().sum().sum() / (processed_data.shape[0] * processed_data.shape[1])
        new_duplicate_count = processed_data.duplicated().sum()
        
        # Calculate new quality score
        new_quality_score = 1.0 - (new_missing_ratio * 0.5) - min(0.2, new_duplicate_count / len(processed_data))
        
        improvement = new_quality_score - original_profile.get("initial_quality_score", 0.5)
        
        recommendations = []
        if new_missing_ratio > 0.01:
            recommendations.append("Consider additional missing value imputation")
        if processed_data.shape[1] > 50:
            recommendations.append("Consider feature selection for high-dimensional data")
        if len(processed_data) < 1000:
            recommendations.append("Consider data augmentation for small dataset")
        
        return {
            "quality_score": new_quality_score,
            "improvement": improvement,
            "missing_ratio": new_missing_ratio,
            "duplicate_count": new_duplicate_count,
            "recommendations": recommendations,
            "processing_success": improvement > 0
        }
    
    def _generate_intelligence_insights(self, 
                                      data_profile: Dict[str, Any],
                                      strategy: Dict[str, Any],
                                      assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive intelligence insights."""
        return {
            "data_readiness": assessment["quality_score"] > 0.8,
            "preprocessing_effectiveness": assessment["improvement"] > 0.1,
            "recommended_ml_approaches": self._recommend_ml_approaches(data_profile, assessment),
            "potential_challenges": self._identify_potential_challenges(data_profile, assessment),
            "optimization_suggestions": self._suggest_optimizations(data_profile, strategy, assessment)
        }
    
    def _recommend_ml_approaches(self, 
                               data_profile: Dict[str, Any],
                               assessment: Dict[str, Any]) -> List[str]:
        """Recommend ML approaches based on data characteristics."""
        recommendations = []
        
        if data_profile.get("shape", [0])[0] < 1000:
            recommendations.append("Simple algorithms (logistic regression, decision trees)")
        elif data_profile.get("shape", [0])[0] > 10000:
            recommendations.append("Ensemble methods or deep learning")
        else:
            recommendations.append("Standard ML algorithms (random forest, SVM)")
        
        if len(data_profile.get("categorical_columns", [])) > 5:
            recommendations.append("Tree-based methods for categorical features")
        
        return recommendations
    
    def _identify_potential_challenges(self, 
                                     data_profile: Dict[str, Any],
                                     assessment: Dict[str, Any]) -> List[str]:
        """Identify potential ML challenges."""
        challenges = []
        
        if assessment["quality_score"] < 0.7:
            challenges.append("Data quality issues may affect model performance")
        
        if data_profile.get("shape", [0, 0])[1] > 100:
            challenges.append("High dimensionality - consider feature selection")
        
        if data_profile.get("missing_ratio", 0) > 0.1:
            challenges.append("Significant missing data may introduce bias")
        
        return challenges
    
    def _suggest_optimizations(self, 
                             data_profile: Dict[str, Any],
                             strategy: Dict[str, Any],
                             assessment: Dict[str, Any]) -> List[str]:
        """Suggest data optimization strategies."""
        suggestions = []
        
        if assessment["quality_score"] < 0.9:
            suggestions.append("Apply additional data cleaning techniques")
        
        if len(data_profile.get("numeric_columns", [])) > 10:
            suggestions.append("Consider dimensionality reduction techniques")
        
        if data_profile.get("shape", [0])[0] < 5000:
            suggestions.append("Consider data augmentation or synthetic data generation")
        
        return suggestions
    
    def _try_load_from_cache(self, source_path: str) -> Optional[pd.DataFrame]:
        """Try to load data from cache."""
        cache_file = self.cache_dir / f"{Path(source_path).stem}_cache.parquet"
        
        if cache_file.exists():
            try:
                # Check if cache is newer than source
                cache_mtime = cache_file.stat().st_mtime
                source_mtime = os.path.getmtime(source_path)
                
                if cache_mtime >= source_mtime:
                    return pd.read_parquet(cache_file)
            except Exception as e:
                self.logger.warning(f"Failed to load from cache: {e}")
        
        return None
    
    def _cache_data(self, source_path: str, data: pd.DataFrame):
        """Cache loaded data."""
        try:
            cache_file = self.cache_dir / f"{Path(source_path).stem}_cache.parquet"
            data.to_parquet(cache_file, index=False)
        except Exception as e:
            self.logger.warning(f"Failed to cache data: {e}")
    
    def _estimate_available_memory(self) -> float:
        """Estimate available system memory in MB."""
        try:
            import psutil
            return psutil.virtual_memory().available / 1024 / 1024
        except ImportError:
            return 4000.0  # Default assumption: 4GB available
    
    def _determine_missing_value_strategy(self, data_profile: Dict[str, Any]) -> str:
        """Determine optimal missing value strategy."""
        missing_ratio = data_profile.get("missing_ratio", 0)
        
        if missing_ratio < 0.05:
            return "drop"
        elif missing_ratio < 0.3:
            return "simple_impute"
        else:
            return "knn_impute"
    
    def _determine_encoding_strategy(self, data_profile: Dict[str, Any]) -> str:
        """Determine optimal categorical encoding strategy."""
        categorical_columns = data_profile.get("categorical_columns", [])
        unique_counts = data_profile.get("unique_counts", {})
        
        max_unique = max([unique_counts.get(col, 0) for col in categorical_columns], default=0)
        
        if max_unique <= 5:
            return "onehot_encoding"
        else:
            return "label_encoding"
    
    def _determine_scaling_strategy(self, data_profile: Dict[str, Any]) -> str:
        """Determine optimal feature scaling strategy."""
        # Use robust scaling if outliers are likely
        numeric_summary = data_profile.get("numeric_summary", {})
        
        # Simple heuristic: if any column has high variance, use robust scaling
        has_outliers = False
        for col, stats in numeric_summary.items():
            if isinstance(stats, dict) and 'std' in stats and 'mean' in stats:
                cv = stats['std'] / (abs(stats['mean']) + 1e-8)  # Coefficient of variation
                if cv > 2:  # High variance
                    has_outliers = True
                    break
        
        return "robust_scaling" if has_outliers else "standard_scaling"
    
    def _assess_outlier_severity(self, data_profile: Dict[str, Any]) -> float:
        """Assess severity of outliers in the data."""
        # Simplified assessment based on data characteristics
        numeric_columns = data_profile.get("numeric_columns", [])
        if not numeric_columns:
            return 0.0
        
        # Estimate outlier severity based on number of numeric columns and data size
        outlier_likelihood = min(0.3, len(numeric_columns) * 0.05)
        return outlier_likelihood
    
    def _identify_quality_issues(self, 
                               basic_profile: Dict[str, Any],
                               advanced_profile: Dict[str, Any]) -> List[str]:
        """Identify data quality issues."""
        issues = []
        
        if advanced_profile.get("missing_ratio", 0) > 0.1:
            issues.append("High missing data ratio")
        
        if advanced_profile.get("duplicate_rows", 0) > 0:
            issues.append("Duplicate rows detected")
        
        if basic_profile.get("shape", [0])[0] < 100:
            issues.append("Very small dataset size")
        
        return issues
    
    def _identify_preprocessing_needs(self, 
                                    data: pd.DataFrame,
                                    advanced_profile: Dict[str, Any]) -> List[str]:
        """Identify preprocessing needs."""
        needs = []
        
        if advanced_profile.get("missing_ratio", 0) > 0:
            needs.append("Missing value imputation")
        
        if len(advanced_profile.get("categorical_columns", [])) > 0:
            needs.append("Categorical encoding")
        
        if len(advanced_profile.get("numeric_columns", [])) > 1:
            needs.append("Feature scaling")
        
        return needs
    
    def _identify_feature_opportunities(self, advanced_profile: Dict[str, Any]) -> List[str]:
        """Identify feature engineering opportunities."""
        opportunities = []
        
        numeric_cols = len(advanced_profile.get("numeric_columns", []))
        categorical_cols = len(advanced_profile.get("categorical_columns", []))
        
        if numeric_cols > 2:
            opportunities.append("Interaction features between numeric variables")
        
        if categorical_cols > 0 and numeric_cols > 0:
            opportunities.append("Group-based statistical features")
        
        if numeric_cols > 5:
            opportunities.append("Polynomial features for non-linear relationships")
        
        return opportunities
    
    def _estimate_quality_improvement(self, preprocessing_steps: List[Dict[str, Any]]) -> float:
        """Estimate expected quality improvement from preprocessing steps."""
        improvement = 0.0
        
        for step in preprocessing_steps:
            step_name = step.get("step", "")
            priority = step.get("priority", "low")
            
            if priority == "high":
                improvement += 0.1
            elif priority == "medium":
                improvement += 0.05
            else:
                improvement += 0.02
        
        return min(0.4, improvement)  # Cap at 40% improvement