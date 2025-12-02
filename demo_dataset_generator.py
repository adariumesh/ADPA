"""
Realistic Demo Dataset Generator for ADPA Autonomous Agent Demonstration
Creates comprehensive customer churn dataset with realistic patterns and correlations.
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import os

class ADPADemoDatasetGenerator:
    """
    Generates realistic datasets for demonstrating ADPA's autonomous capabilities.
    Creates datasets with realistic patterns, missing values, and business logic.
    """
    
    def __init__(self, seed: int = 42):
        """Initialize the dataset generator with a random seed for reproducibility."""
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)
    
    def create_customer_churn_dataset(self, n_customers: int = 1500) -> Dict[str, Any]:
        """
        Create a realistic customer churn dataset with complex patterns.
        
        Args:
            n_customers: Number of customers to generate
            
        Returns:
            Dictionary containing dataset, metadata, and business context
        """
        print(f"🔄 Generating customer churn dataset with {n_customers} customers...")
        
        # Customer demographics with realistic distributions
        ages = np.random.normal(42, 15, n_customers).clip(18, 85).astype(int)
        
        # Income based on age with some correlation
        base_income = 30000 + (ages - 18) * 800 + np.random.normal(0, 15000, n_customers)
        annual_income = base_income.clip(20000, 200000)
        
        # Tenure with churn correlation (longer tenure = less likely to churn)
        tenure_months = np.random.exponential(24, n_customers).clip(1, 120).astype(int)
        
        # Monthly charges based on income and tenure
        base_charges = 20 + (annual_income / 100000) * 80 + np.random.gamma(2, 15, n_customers)
        monthly_charges = base_charges.clip(15, 150)
        
        # Total charges based on tenure and monthly charges with some variation
        total_charges = tenure_months * monthly_charges * np.random.uniform(0.8, 1.2, n_customers)
        
        # Contract types with business logic
        contract_weights = [0.5, 0.3, 0.2]  # Month-to-month, One year, Two year
        contract_types = np.random.choice(['Month-to-month', 'One year', 'Two year'], 
                                        n_customers, p=contract_weights)
        
        # Services with correlations
        internet_service = np.random.choice(['DSL', 'Fiber optic', 'No'], 
                                          n_customers, p=[0.3, 0.45, 0.25])
        
        # Phone service correlation with internet
        phone_service = np.where(internet_service == 'No', 
                               np.random.choice(['Yes', 'No'], n_customers, p=[0.9, 0.1]),
                               np.random.choice(['Yes', 'No'], n_customers, p=[0.7, 0.3]))
        
        # Multiple lines based on phone service
        multiple_lines = np.where(phone_service == 'No', 'No phone service',
                                np.random.choice(['Yes', 'No'], n_customers, p=[0.4, 0.6]))
        
        # Online security, backup, etc. based on internet service
        online_security = np.where(internet_service == 'No', 'No internet service',
                                 np.random.choice(['Yes', 'No'], n_customers, p=[0.3, 0.7]))
        
        online_backup = np.where(internet_service == 'No', 'No internet service',
                               np.random.choice(['Yes', 'No'], n_customers, p=[0.35, 0.65]))
        
        device_protection = np.where(internet_service == 'No', 'No internet service',
                                   np.random.choice(['Yes', 'No'], n_customers, p=[0.32, 0.68]))
        
        tech_support = np.where(internet_service == 'No', 'No internet service',
                              np.random.choice(['Yes', 'No'], n_customers, p=[0.28, 0.72]))
        
        streaming_tv = np.where(internet_service == 'No', 'No internet service',
                              np.random.choice(['Yes', 'No'], n_customers, p=[0.4, 0.6]))
        
        streaming_movies = np.where(internet_service == 'No', 'No internet service',
                                  np.random.choice(['Yes', 'No'], n_customers, p=[0.38, 0.62]))
        
        # Payment methods with some business logic
        payment_methods = np.random.choice(['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)'],
                                         n_customers, p=[0.35, 0.15, 0.25, 0.25])
        
        # Paperless billing correlation with payment method
        paperless_billing = np.where(payment_methods.isin(['Bank transfer (automatic)', 'Credit card (automatic)']),
                                    np.random.choice(['Yes', 'No'], n_customers, p=[0.8, 0.2]),
                                    np.random.choice(['Yes', 'No'], n_customers, p=[0.5, 0.5]))
        
        # Gender and other demographics
        gender = np.random.choice(['Male', 'Female'], n_customers)
        senior_citizen = (ages >= 65).astype(int)
        partner = np.random.choice(['Yes', 'No'], n_customers, p=[0.55, 0.45])
        dependents = np.where(partner == 'Yes', 
                            np.random.choice(['Yes', 'No'], n_customers, p=[0.4, 0.6]),
                            np.random.choice(['Yes', 'No'], n_customers, p=[0.15, 0.85]))
        
        # Calculate churn with realistic business logic
        churn_probability = self._calculate_churn_probability(
            ages, tenure_months, monthly_charges, contract_types,
            internet_service, payment_methods, senior_citizen
        )
        
        churn = np.random.binomial(1, churn_probability, n_customers)
        
        # Create customer IDs
        customer_ids = [f"CUST_{i:06d}" for i in range(1, n_customers + 1)]
        
        # Build the dataset
        df = pd.DataFrame({
            'CustomerID': customer_ids,
            'Gender': gender,
            'SeniorCitizen': senior_citizen,
            'Partner': partner,
            'Dependents': dependents,
            'Age': ages,
            'Tenure': tenure_months,
            'PhoneService': phone_service,
            'MultipleLines': multiple_lines,
            'InternetService': internet_service,
            'OnlineSecurity': online_security,
            'OnlineBackup': online_backup,
            'DeviceProtection': device_protection,
            'TechSupport': tech_support,
            'StreamingTV': streaming_tv,
            'StreamingMovies': streaming_movies,
            'Contract': contract_types,
            'PaperlessBilling': paperless_billing,
            'PaymentMethod': payment_methods,
            'MonthlyCharges': np.round(monthly_charges, 2),
            'TotalCharges': np.round(total_charges, 2),
            'AnnualIncome': np.round(annual_income, 0),
            'Churn': churn
        })
        
        # Add realistic missing values (15% missing data as specified)
        df = self._add_realistic_missing_values(df, missing_ratio=0.15)
        
        # Create business context and metadata
        metadata = {
            "dataset_info": {
                "name": "Customer Churn Prediction Dataset",
                "description": "Realistic telecom customer churn dataset for ML pipeline demonstration",
                "size": df.shape,
                "target_variable": "Churn",
                "problem_type": "Binary Classification",
                "business_context": "Predict customer churn to enable proactive retention strategies"
            },
            "data_characteristics": {
                "total_customers": n_customers,
                "churn_rate": f"{churn.mean():.1%}",
                "missing_data_percentage": f"{df.isnull().sum().sum() / (df.shape[0] * df.shape[1]):.1%}",
                "numeric_features": df.select_dtypes(include=[np.number]).columns.tolist(),
                "categorical_features": df.select_dtypes(include=['object']).columns.tolist()
            },
            "business_insights": {
                "avg_monthly_revenue_per_customer": f"${monthly_charges.mean():.2f}",
                "avg_customer_lifetime_value": f"${(monthly_charges * tenure_months).mean():.2f}",
                "high_risk_segments": [
                    "Month-to-month contracts",
                    "Electronic check payment method",
                    "No online security services",
                    "Senior citizens with short tenure"
                ]
            },
            "expected_ml_performance": {
                "baseline_accuracy": "73-76%",
                "expected_advanced_model_accuracy": "85-92%",
                "key_predictive_features": ["Tenure", "Contract", "MonthlyCharges", "PaymentMethod", "InternetService"]
            }
        }
        
        print(f"✅ Generated dataset: {df.shape[0]} customers, {df.shape[1]} features")
        print(f"📊 Churn rate: {churn.mean():.1%}")
        print(f"🔍 Missing data: {df.isnull().sum().sum() / (df.shape[0] * df.shape[1]):.1%}")
        
        return {
            "dataset": df,
            "metadata": metadata,
            "generation_timestamp": datetime.now().isoformat()
        }
    
    def create_sales_forecasting_dataset(self, n_records: int = 2000) -> Dict[str, Any]:
        """Create realistic sales forecasting dataset."""
        print(f"🔄 Generating sales forecasting dataset with {n_records} records...")
        
        # Time series data
        start_date = datetime(2020, 1, 1)
        dates = [start_date + timedelta(days=x) for x in range(n_records)]
        
        # Seasonal patterns
        day_of_year = np.array([d.timetuple().tm_yday for d in dates])
        seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * day_of_year / 365)
        
        # Trend component
        trend = 1000 + np.arange(n_records) * 0.5
        
        # Random component
        random_component = np.random.normal(0, 100, n_records)
        
        # Weekly patterns
        weekday = np.array([d.weekday() for d in dates])
        weekly_factor = np.where(weekday < 5, 1.2, 0.8)  # Higher sales on weekdays
        
        # Calculate sales
        sales = trend * seasonal_factor * weekly_factor + random_component
        sales = np.maximum(sales, 0)  # Ensure non-negative sales
        
        # Additional features
        temperature = 20 + 15 * np.sin(2 * np.pi * day_of_year / 365) + np.random.normal(0, 5, n_records)
        marketing_spend = np.random.exponential(500, n_records)
        promotion_active = np.random.binomial(1, 0.2, n_records)
        
        # Adjust sales based on marketing and promotions
        sales += marketing_spend * 0.5 + promotion_active * 200
        
        df = pd.DataFrame({
            'Date': dates,
            'Sales': np.round(sales, 2),
            'Temperature': np.round(temperature, 1),
            'MarketingSpend': np.round(marketing_spend, 2),
            'PromotionActive': promotion_active,
            'DayOfWeek': weekday,
            'Month': [d.month for d in dates],
            'Quarter': [(d.month - 1) // 3 + 1 for d in dates]
        })
        
        # Add missing values
        df = self._add_realistic_missing_values(df, missing_ratio=0.08)
        
        metadata = {
            "dataset_info": {
                "name": "Sales Forecasting Dataset",
                "description": "Time series sales data for forecasting demonstration",
                "size": df.shape,
                "target_variable": "Sales",
                "problem_type": "Time Series Forecasting",
                "business_context": "Forecast daily sales for inventory and planning optimization"
            },
            "expected_ml_performance": {
                "baseline_mae": "150-200",
                "expected_advanced_model_mae": "80-120",
                "key_predictive_features": ["Date", "Temperature", "MarketingSpend", "PromotionActive"]
            }
        }
        
        print(f"✅ Generated sales dataset: {df.shape[0]} records, {df.shape[1]} features")
        
        return {
            "dataset": df,
            "metadata": metadata,
            "generation_timestamp": datetime.now().isoformat()
        }
    
    def create_fraud_detection_dataset(self, n_transactions: int = 1200) -> Dict[str, Any]:
        """Create realistic fraud detection dataset."""
        print(f"🔄 Generating fraud detection dataset with {n_transactions} transactions...")
        
        # Transaction amounts with different distributions for fraud vs normal
        normal_amounts = np.random.lognormal(4, 1.5, int(n_transactions * 0.98))
        fraud_amounts = np.concatenate([
            np.random.uniform(1, 50, int(n_transactions * 0.01)),  # Small fraudulent transactions
            np.random.uniform(5000, 50000, int(n_transactions * 0.01))  # Large fraudulent transactions
        ])
        
        amounts = np.concatenate([normal_amounts, fraud_amounts])
        amounts = amounts[:n_transactions]
        
        # Create fraud labels
        fraud_labels = np.concatenate([
            np.zeros(len(normal_amounts)), 
            np.ones(len(fraud_amounts))
        ])[:n_transactions]
        
        # Shuffle
        indices = np.random.permutation(len(amounts))
        amounts = amounts[indices]
        fraud_labels = fraud_labels[indices]
        
        # Additional features
        transaction_hours = np.random.randint(0, 24, n_transactions)
        # Fraud more likely at odd hours
        fraud_hours = np.where(fraud_labels == 1, 
                             np.random.choice([0, 1, 2, 3, 22, 23], len(fraud_labels[fraud_labels == 1])),
                             transaction_hours[fraud_labels == 1])
        transaction_hours[fraud_labels == 1] = fraud_hours
        
        merchant_categories = np.random.choice(['grocery', 'gas_station', 'restaurant', 'online', 'retail'], n_transactions)
        customer_ages = np.random.normal(40, 15, n_transactions).clip(18, 90).astype(int)
        days_since_last_transaction = np.random.exponential(2, n_transactions).clip(0, 30)
        
        df = pd.DataFrame({
            'TransactionID': [f"TXN_{i:08d}" for i in range(1, n_transactions + 1)],
            'Amount': np.round(amounts, 2),
            'TransactionHour': transaction_hours,
            'MerchantCategory': merchant_categories,
            'CustomerAge': customer_ages,
            'DaysSinceLastTransaction': np.round(days_since_last_transaction, 1),
            'IsFraud': fraud_labels.astype(int)
        })
        
        # Add missing values
        df = self._add_realistic_missing_values(df, missing_ratio=0.05)
        
        metadata = {
            "dataset_info": {
                "name": "Credit Card Fraud Detection Dataset",
                "description": "Realistic transaction data for fraud detection demonstration",
                "size": df.shape,
                "target_variable": "IsFraud",
                "problem_type": "Binary Classification (Imbalanced)",
                "business_context": "Detect fraudulent transactions in real-time to prevent financial losses"
            },
            "data_characteristics": {
                "fraud_rate": f"{fraud_labels.mean():.1%}",
                "class_imbalance": "Highly imbalanced dataset typical of fraud detection"
            },
            "expected_ml_performance": {
                "baseline_accuracy": "98%+ (due to class imbalance)",
                "target_metric": "F1-Score and AUC-ROC",
                "expected_f1_score": "0.75-0.90",
                "key_predictive_features": ["Amount", "TransactionHour", "DaysSinceLastTransaction"]
            }
        }
        
        print(f"✅ Generated fraud dataset: {df.shape[0]} transactions, {fraud_labels.mean():.1%} fraud rate")
        
        return {
            "dataset": df,
            "metadata": metadata,
            "generation_timestamp": datetime.now().isoformat()
        }
    
    def _calculate_churn_probability(self, ages, tenure_months, monthly_charges, contract_types,
                                   internet_service, payment_methods, senior_citizen):
        """Calculate realistic churn probabilities based on business logic."""
        
        # Base probability
        base_prob = 0.27  # 27% base churn rate
        
        # Tenure effect (longer tenure = less likely to churn)
        tenure_effect = -0.01 * tenure_months
        
        # Contract effect
        contract_effect = np.where(contract_types == 'Month-to-month', 0.15,
                                 np.where(contract_types == 'One year', 0.05, -0.05))
        
        # Payment method effect
        payment_effect = np.where(payment_methods == 'Electronic check', 0.12,
                                np.where(payment_methods == 'Mailed check', 0.08, -0.02))
        
        # Price sensitivity
        price_effect = (monthly_charges - 65) / 100 * 0.1
        
        # Senior citizen effect
        senior_effect = np.where(senior_citizen == 1, 0.05, 0)
        
        # Internet service effect
        internet_effect = np.where(internet_service == 'Fiber optic', 0.08,
                                 np.where(internet_service == 'DSL', 0.02, -0.05))
        
        total_prob = base_prob + tenure_effect + contract_effect + payment_effect + price_effect + senior_effect + internet_effect
        
        return np.clip(total_prob, 0.05, 0.95)
    
    def _add_realistic_missing_values(self, df: pd.DataFrame, missing_ratio: float = 0.15) -> pd.DataFrame:
        """Add realistic missing values to the dataset."""
        df_with_missing = df.copy()
        
        # Columns that are more likely to have missing values
        high_missing_cols = ['TotalCharges', 'AnnualIncome']
        medium_missing_cols = ['Age', 'Tenure']
        
        for col in df.columns:
            if col in high_missing_cols:
                missing_prob = missing_ratio * 2
            elif col in medium_missing_cols:
                missing_prob = missing_ratio * 1.5
            else:
                missing_prob = missing_ratio * 0.5
            
            # Don't add missing values to ID columns or target variable
            if col in ['CustomerID', 'TransactionID', 'Churn', 'IsFraud', 'Sales']:
                continue
            
            missing_mask = np.random.random(len(df)) < missing_prob
            df_with_missing.loc[missing_mask, col] = np.nan
        
        return df_with_missing
    
    def save_datasets(self, datasets: Dict[str, Any], output_dir: str = "./demo_datasets") -> Dict[str, str]:
        """Save generated datasets to files."""
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = {}
        
        for dataset_name, dataset_info in datasets.items():
            # Save CSV
            csv_path = os.path.join(output_dir, f"{dataset_name}.csv")
            dataset_info["dataset"].to_csv(csv_path, index=False)
            
            # Save metadata
            metadata_path = os.path.join(output_dir, f"{dataset_name}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(dataset_info["metadata"], f, indent=2)
            
            saved_files[dataset_name] = {
                "csv_path": csv_path,
                "metadata_path": metadata_path
            }
            
            print(f"💾 Saved {dataset_name} to {csv_path}")
        
        return saved_files


def generate_all_demo_datasets():
    """Generate all demo datasets for ADPA demonstration."""
    print("🚀 Generating comprehensive demo datasets for ADPA autonomous agent demonstration...")
    print("=" * 80)
    
    generator = ADPADemoDatasetGenerator(seed=42)
    
    # Generate datasets
    datasets = {
        "customer_churn": generator.create_customer_churn_dataset(1500),
        "sales_forecasting": generator.create_sales_forecasting_dataset(2000),
        "fraud_detection": generator.create_fraud_detection_dataset(1200)
    }
    
    # Save datasets
    saved_files = generator.save_datasets(datasets, "./demo_datasets")
    
    print("\n" + "=" * 80)
    print("✅ ALL DEMO DATASETS GENERATED SUCCESSFULLY")
    print("=" * 80)
    
    for dataset_name, paths in saved_files.items():
        print(f"📁 {dataset_name.replace('_', ' ').title()}:")
        print(f"   📊 Data: {paths['csv_path']}")
        print(f"   📋 Metadata: {paths['metadata_path']}")
    
    print("\n🎯 Datasets ready for autonomous agent demonstration!")
    return datasets, saved_files


if __name__ == "__main__":
    generate_all_demo_datasets()