"""
Local Test Script for ADPA Retail Sales Forecasting Dataset
Tests the complete ML pipeline locally before cloud deployment.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

def load_and_explore_data(filepath: str) -> pd.DataFrame:
    """Load and explore the retail sales dataset."""
    print("=" * 80)
    print("📊 LOADING AND EXPLORING DATA")
    print("=" * 80)
    
    df = pd.read_csv(filepath)
    
    print(f"\n📁 Dataset Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\n📋 Columns:\n{df.columns.tolist()}")
    print(f"\n📈 Data Types:\n{df.dtypes}")
    print(f"\n🔍 First 5 rows:")
    print(df.head())
    
    print(f"\n📊 Target Variable (DailySales) Statistics:")
    print(df['DailySales'].describe())
    
    print(f"\n❓ Missing Values:")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({'Missing': missing, 'Percentage': missing_pct})
    print(missing_df[missing_df['Missing'] > 0])
    
    return df


def preprocess_data(df: pd.DataFrame) -> tuple:
    """Preprocess the data for ML training."""
    print("\n" + "=" * 80)
    print("🔧 PREPROCESSING DATA")
    print("=" * 80)
    
    df_processed = df.copy()
    
    # Handle missing values
    print("\n1️⃣ Handling missing values...")
    
    # Numeric columns - fill with median
    numeric_cols = df_processed.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df_processed[col].isnull().sum() > 0:
            median_val = df_processed[col].median()
            df_processed[col].fillna(median_val, inplace=True)
            print(f"   - Filled {col} with median: {median_val:.2f}")
    
    # Categorical columns - fill with mode
    cat_cols = ['StoreSize', 'Region']
    for col in cat_cols:
        if col in df_processed.columns and df_processed[col].isnull().sum() > 0:
            mode_val = df_processed[col].mode()[0]
            df_processed[col].fillna(mode_val, inplace=True)
            print(f"   - Filled {col} with mode: {mode_val}")
    
    # Encode categorical variables
    print("\n2️⃣ Encoding categorical variables...")
    le_store = LabelEncoder()
    le_size = LabelEncoder()
    le_region = LabelEncoder()
    
    df_processed['StoreID_encoded'] = le_store.fit_transform(df_processed['StoreID'])
    df_processed['StoreSize_encoded'] = le_size.fit_transform(df_processed['StoreSize'])
    df_processed['Region_encoded'] = le_region.fit_transform(df_processed['Region'])
    
    print(f"   - StoreID: {len(le_store.classes_)} unique values")
    print(f"   - StoreSize: {le_size.classes_}")
    print(f"   - Region: {le_region.classes_}")
    
    # Feature engineering
    print("\n3️⃣ Feature engineering...")
    
    # Convert Date to datetime and extract features
    df_processed['Date'] = pd.to_datetime(df_processed['Date'])
    df_processed['DayOfYear'] = df_processed['Date'].dt.dayofyear
    df_processed['WeekOfYear'] = df_processed['Date'].dt.isocalendar().week.astype(int)
    
    # Create lag features (previous day sales per store)
    df_processed = df_processed.sort_values(['StoreID', 'Date'])
    df_processed['PrevDaySales'] = df_processed.groupby('StoreID')['DailySales'].shift(1)
    df_processed['PrevDaySales'].fillna(df_processed['DailySales'].mean(), inplace=True)
    
    # Rolling average (7-day)
    df_processed['RollingAvg7'] = df_processed.groupby('StoreID')['DailySales'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )
    
    print(f"   - Added DayOfYear, WeekOfYear")
    print(f"   - Added PrevDaySales (lag feature)")
    print(f"   - Added RollingAvg7 (7-day rolling average)")
    
    # Select features for modeling
    feature_cols = [
        'StoreID_encoded', 'Transactions', 'AvgTransactionValue', 'FootTraffic',
        'InventoryLevel', 'StockoutEvents', 'IsPromotion', 'MarketingSpend',
        'Temperature', 'CompetitorPriceIndex', 'DayOfWeek', 'Month', 'Quarter',
        'IsWeekend', 'IsHolidaySeason', 'StoreSize_encoded', 'Region_encoded',
        'DayOfYear', 'WeekOfYear', 'PrevDaySales', 'RollingAvg7'
    ]
    
    X = df_processed[feature_cols]
    y = df_processed['DailySales']
    
    print(f"\n✅ Final feature set: {len(feature_cols)} features")
    print(f"   Features: {feature_cols}")
    
    return X, y, df_processed


def train_and_evaluate_models(X: pd.DataFrame, y: pd.Series) -> dict:
    """Train multiple models and evaluate their performance."""
    print("\n" + "=" * 80)
    print("🤖 TRAINING AND EVALUATING MODELS")
    print("=" * 80)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"\n📊 Train/Test Split:")
    print(f"   - Training samples: {len(X_train)}")
    print(f"   - Testing samples: {len(X_test)}")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Define models
    models = {
        'Linear Regression': LinearRegression(),
        'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n🔄 Training {name}...")
        
        # Use scaled data for Linear Regression, original for tree-based
        if name == 'Linear Regression':
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
        
        results[name] = {
            'MAE': mae,
            'RMSE': rmse,
            'R2': r2,
            'MAPE': mape,
            'model': model
        }
        
        print(f"   ✅ {name} Results:")
        print(f"      - MAE:  ${mae:,.2f}")
        print(f"      - RMSE: ${rmse:,.2f}")
        print(f"      - R²:   {r2:.4f}")
        print(f"      - MAPE: {mape:.2f}%")
    
    return results, X_test, y_test


def analyze_feature_importance(results: dict, feature_names: list):
    """Analyze feature importance from tree-based models."""
    print("\n" + "=" * 80)
    print("📊 FEATURE IMPORTANCE ANALYSIS")
    print("=" * 80)
    
    if 'Random Forest' in results:
        rf_model = results['Random Forest']['model']
        importances = rf_model.feature_importances_
        
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances
        }).sort_values('Importance', ascending=False)
        
        print("\n🌲 Random Forest - Top 10 Features:")
        for i, row in importance_df.head(10).iterrows():
            print(f"   {row['Feature']:25} : {row['Importance']:.4f}")
    
    if 'Gradient Boosting' in results:
        gb_model = results['Gradient Boosting']['model']
        importances = gb_model.feature_importances_
        
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances
        }).sort_values('Importance', ascending=False)
        
        print("\n🚀 Gradient Boosting - Top 10 Features:")
        for i, row in importance_df.head(10).iterrows():
            print(f"   {row['Feature']:25} : {row['Importance']:.4f}")


def generate_summary_report(results: dict):
    """Generate a summary report of the local testing."""
    print("\n" + "=" * 80)
    print("📋 SUMMARY REPORT")
    print("=" * 80)
    
    print("\n📊 Model Performance Comparison:")
    print("-" * 70)
    print(f"{'Model':<25} {'MAE':>12} {'RMSE':>12} {'R²':>10} {'MAPE':>10}")
    print("-" * 70)
    
    best_model = None
    best_mae = float('inf')
    
    for name, metrics in results.items():
        print(f"{name:<25} ${metrics['MAE']:>10,.2f} ${metrics['RMSE']:>10,.2f} {metrics['R2']:>10.4f} {metrics['MAPE']:>9.2f}%")
        if metrics['MAE'] < best_mae:
            best_mae = metrics['MAE']
            best_model = name
    
    print("-" * 70)
    
    print(f"\n🏆 Best Model: {best_model}")
    print(f"   - MAE: ${results[best_model]['MAE']:,.2f}")
    print(f"   - MAPE: {results[best_model]['MAPE']:.2f}%")
    
    # Compare with expected performance from metadata
    print("\n📈 Performance vs Expected (from metadata):")
    print(f"   - Expected Baseline MAE: $1,500 - $2,000")
    print(f"   - Expected Advanced Model MAE: $800 - $1,200")
    print(f"   - Achieved MAE: ${results[best_model]['MAE']:,.2f}")
    
    if results[best_model]['MAE'] < 1200:
        print("   ✅ EXCEEDS EXPECTATIONS!")
    elif results[best_model]['MAE'] < 2000:
        print("   ✅ MEETS EXPECTATIONS")
    else:
        print("   ⚠️ Below expectations - may need feature engineering improvements")
    
    print("\n" + "=" * 80)
    print("✅ LOCAL TESTING COMPLETE")
    print("=" * 80)
    print("\n🎯 Next Steps:")
    print("   1. Deploy to AWS S3 for cloud processing")
    print("   2. Run AWS Glue ETL jobs for data cleaning")
    print("   3. Train models on SageMaker for production")
    print("   4. Set up CloudWatch monitoring")


def main():
    """Main function to run the local testing pipeline."""
    print("\n" + "=" * 80)
    print("🚀 ADPA LOCAL TESTING PIPELINE")
    print("   Retail Sales Forecasting Dataset")
    print("=" * 80)
    
    # Load data
    df = load_and_explore_data("./demo_datasets/retail_sales_forecasting.csv")
    
    # Preprocess
    X, y, df_processed = preprocess_data(df)
    
    # Train and evaluate
    results, X_test, y_test = train_and_evaluate_models(X, y)
    
    # Feature importance
    analyze_feature_importance(results, X.columns.tolist())
    
    # Summary
    generate_summary_report(results)
    
    return results


if __name__ == "__main__":
    results = main()
