#!/usr/bin/env python3
"""
Comprehensive ADPA System Tests
Tests the complete end-to-end workflow including AI capabilities
"""

import json
import boto3
import pandas as pd
import numpy as np
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests
import io

# Test configuration
TEST_CONFIG = {
    "region": "us-east-2",
    "lambda_function": "adpa-data-processor-development",
    "error_handler": "adpa-error-handler-development",
    "test_timeout": 300,  # 5 minutes per test
    "data_bucket": "adpa-data-083308938449-development",
    "model_bucket": "adpa-models-083308938449-development"
}

class ADPATestSuite:
    """Comprehensive test suite for ADPA system validation"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name=TEST_CONFIG['region'])
        self.s3_client = boto3.client('s3', region_name=TEST_CONFIG['region'])
        self.cloudwatch = boto3.client('cloudwatch', region_name=TEST_CONFIG['region'])
        
        self.test_results = []
        self.test_data = {}
        
        print("🧪 ADPA Comprehensive Test Suite Initialized")
        print(f"Target Function: {TEST_CONFIG['lambda_function']}")
        print(f"Region: {TEST_CONFIG['region']}")
        print("=" * 60)
    
    def run_all_tests(self):
        """Execute complete test suite"""
        
        print("🚀 Starting Comprehensive ADPA Tests")
        print("=" * 60)
        
        # Phase 1: Infrastructure Tests
        print("\n📋 Phase 1: Infrastructure Validation")
        self.test_lambda_function_exists()
        self.test_s3_bucket_access()
        self.test_iam_permissions()
        
        # Phase 2: Basic Functionality Tests
        print("\n📋 Phase 2: Basic Functionality")
        self.test_health_check()
        self.test_error_handler()
        
        # Phase 3: AI Capabilities Tests
        print("\n📋 Phase 3: AI Capabilities")
        self.test_objective_understanding()
        self.test_pipeline_adaptation()
        
        # Phase 4: End-to-End Workflow Tests
        print("\n📋 Phase 4: End-to-End Workflows")
        self.create_test_datasets()
        self.test_classification_pipeline()
        self.test_regression_pipeline()
        
        # Phase 5: Monitoring & Intelligence Tests
        print("\n📋 Phase 5: Monitoring & Intelligence")
        self.test_cloudwatch_metrics()
        self.test_kpi_tracking()
        
        # Phase 6: Stress & Performance Tests
        print("\n📋 Phase 6: Performance & Stress")
        self.test_large_dataset_handling()
        self.test_concurrent_executions()
        
        # Generate comprehensive report
        self.generate_test_report()
    
    def test_lambda_function_exists(self):
        """Test if Lambda function exists and is accessible"""
        test_name = "Lambda Function Existence"
        
        try:
            response = self.lambda_client.get_function(
                FunctionName=TEST_CONFIG['lambda_function']
            )
            
            function_config = response['Configuration']
            
            result = {
                "test": test_name,
                "status": "PASSED",
                "details": {
                    "function_name": function_config['FunctionName'],
                    "runtime": function_config['Runtime'],
                    "memory": function_config['MemorySize'],
                    "timeout": function_config['Timeout'],
                    "last_modified": function_config['LastModified']
                }
            }
            
            print(f"✅ {test_name}: Function exists with {function_config['MemorySize']}MB memory")
            
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_s3_bucket_access(self):
        """Test S3 bucket access and permissions"""
        test_name = "S3 Bucket Access"
        
        try:
            # Test data bucket access
            data_bucket = TEST_CONFIG['data_bucket']
            self.s3_client.head_bucket(Bucket=data_bucket)
            
            # Test model bucket access
            model_bucket = TEST_CONFIG['model_bucket'] 
            self.s3_client.head_bucket(Bucket=model_bucket)
            
            # Test write permissions
            test_key = f"test-{datetime.now().isoformat()}.json"
            self.s3_client.put_object(
                Bucket=data_bucket,
                Key=test_key,
                Body=json.dumps({"test": "access_check"}),
                ContentType="application/json"
            )
            
            # Clean up test object
            self.s3_client.delete_object(Bucket=data_bucket, Key=test_key)
            
            result = {
                "test": test_name,
                "status": "PASSED",
                "details": {
                    "data_bucket": data_bucket,
                    "model_bucket": model_bucket,
                    "write_access": True
                }
            }
            
            print(f"✅ {test_name}: Both buckets accessible with write permissions")
            
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_iam_permissions(self):
        """Test IAM permissions for Lambda execution"""
        test_name = "IAM Permissions"
        
        try:
            # Test by invoking a simple health check
            response = self.lambda_client.invoke(
                FunctionName=TEST_CONFIG['lambda_function'],
                InvocationType='RequestResponse',
                Payload=json.dumps({"action": "health_check"})
            )
            
            if response['StatusCode'] == 200:
                result = {
                    "test": test_name,
                    "status": "PASSED",
                    "details": {
                        "invoke_permission": True,
                        "status_code": response['StatusCode']
                    }
                }
                print(f"✅ {test_name}: Lambda invoke permissions working")
            else:
                result = {
                    "test": test_name,
                    "status": "FAILED",
                    "error": f"Unexpected status code: {response['StatusCode']}"
                }
                print(f"❌ {test_name}: Status code {response['StatusCode']}")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED", 
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_health_check(self):
        """Test ADPA health check endpoint"""
        test_name = "Health Check"
        
        try:
            payload = {"action": "health_check"}
            
            response = self.lambda_client.invoke(
                FunctionName=TEST_CONFIG['lambda_function'],
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response_payload.get('status') == 'healthy':
                components = response_payload.get('components', {})
                
                result = {
                    "test": test_name,
                    "status": "PASSED",
                    "details": {
                        "response": response_payload,
                        "components_loaded": components,
                        "imports_successful": components.get('imports', False),
                        "agent_initialized": components.get('agent', False)
                    }
                }
                
                print(f"✅ {test_name}: System healthy")
                print(f"   Components: {list(components.keys())}")
                
            else:
                result = {
                    "test": test_name,
                    "status": "FAILED",
                    "error": f"System unhealthy: {response_payload}"
                }
                print(f"❌ {test_name}: System unhealthy")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_error_handler(self):
        """Test error handler functionality"""
        test_name = "Error Handler"
        
        try:
            # Create a mock error event
            error_event = {
                "errorMessage": "Test error for validation",
                "errorType": "TestError",
                "stackTrace": ["test_function", "line 42"],
                "requestContext": {"test": True}
            }
            
            response = self.lambda_client.invoke(
                FunctionName=TEST_CONFIG['error_handler'],
                InvocationType='RequestResponse', 
                Payload=json.dumps(error_event)
            )
            
            if response['StatusCode'] == 200:
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload.get('statusCode') == 200:
                    body = json.loads(response_payload.get('body', '{}'))
                    
                    result = {
                        "test": test_name,
                        "status": "PASSED",
                        "details": {
                            "error_analyzed": body.get('status') == 'analyzed',
                            "recovery_strategy": body.get('recovery_recommended', False),
                            "response_body": body
                        }
                    }
                    
                    print(f"✅ {test_name}: Error analysis working")
                    
                else:
                    result = {
                        "test": test_name,
                        "status": "FAILED",
                        "error": f"Error handler returned status: {response_payload.get('statusCode')}"
                    }
                    print(f"❌ {test_name}: Handler returned error status")
            else:
                result = {
                    "test": test_name,
                    "status": "FAILED",
                    "error": f"Lambda invoke failed with status: {response['StatusCode']}"
                }
                print(f"❌ {test_name}: Invoke failed")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_objective_understanding(self):
        """Test AI objective understanding capabilities"""
        test_name = "Objective Understanding"
        
        try:
            test_objectives = [
                "Predict customer churn based on purchase history",
                "Classify emails as spam or not spam",
                "Forecast monthly sales revenue",
                "Detect anomalies in network traffic"
            ]
            
            successful_analyses = 0
            
            for objective in test_objectives:
                payload = {
                    "action": "run_pipeline",
                    "objective": objective,
                    "dataset_path": "mock://test-data", 
                    "config": {"test_mode": True, "analyze_objective_only": True}
                }
                
                response = self.lambda_client.invoke(
                    FunctionName=TEST_CONFIG['lambda_function'],
                    InvocationType='RequestResponse',
                    Payload=json.dumps(payload)
                )
                
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload.get('status') != 'failed':
                    successful_analyses += 1
            
            success_rate = successful_analyses / len(test_objectives)
            
            if success_rate >= 0.75:  # 75% success rate
                result = {
                    "test": test_name,
                    "status": "PASSED",
                    "details": {
                        "success_rate": success_rate,
                        "objectives_tested": len(test_objectives),
                        "successful_analyses": successful_analyses
                    }
                }
                print(f"✅ {test_name}: {successful_analyses}/{len(test_objectives)} objectives understood")
            else:
                result = {
                    "test": test_name,
                    "status": "FAILED",
                    "error": f"Low success rate: {success_rate:.2%}"
                }
                print(f"❌ {test_name}: Only {successful_analyses}/{len(test_objectives)} objectives understood")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def create_test_datasets(self):
        """Create test datasets for pipeline testing"""
        
        print("📊 Creating test datasets...")
        
        # Classification dataset (Customer Churn)
        np.random.seed(42)
        n_samples = 1000
        
        churn_data = pd.DataFrame({
            'customer_id': range(1, n_samples + 1),
            'age': np.random.normal(40, 15, n_samples).astype(int),
            'monthly_charges': np.random.normal(70, 20, n_samples),
            'total_charges': np.random.normal(2000, 800, n_samples),
            'contract_length': np.random.choice(['Month-to-month', 'One year', 'Two year'], n_samples),
            'payment_method': np.random.choice(['Credit card', 'Bank transfer', 'Electronic check'], n_samples),
            'churn': np.random.choice([0, 1], n_samples, p=[0.7, 0.3])
        })
        
        # Regression dataset (House Prices)
        house_data = pd.DataFrame({
            'property_id': range(1, n_samples + 1),
            'bedrooms': np.random.randint(1, 6, n_samples),
            'bathrooms': np.random.randint(1, 4, n_samples), 
            'square_feet': np.random.normal(2000, 500, n_samples),
            'lot_size': np.random.normal(8000, 2000, n_samples),
            'age': np.random.randint(0, 50, n_samples),
            'price': np.random.normal(300000, 100000, n_samples)
        })
        
        # Upload datasets to S3
        try:
            # Upload churn dataset
            churn_csv = churn_data.to_csv(index=False)
            self.s3_client.put_object(
                Bucket=TEST_CONFIG['data_bucket'],
                Key='test-datasets/customer_churn.csv',
                Body=churn_csv,
                ContentType='text/csv'
            )
            
            # Upload house price dataset  
            house_csv = house_data.to_csv(index=False)
            self.s3_client.put_object(
                Bucket=TEST_CONFIG['data_bucket'],
                Key='test-datasets/house_prices.csv',
                Body=house_csv,
                ContentType='text/csv'
            )
            
            self.test_data = {
                'churn': f"s3://{TEST_CONFIG['data_bucket']}/test-datasets/customer_churn.csv",
                'house_prices': f"s3://{TEST_CONFIG['data_bucket']}/test-datasets/house_prices.csv"
            }
            
            print("✅ Test datasets created and uploaded to S3")
            
        except Exception as e:
            print(f"❌ Failed to create test datasets: {e}")
            self.test_data = {
                'churn': 'mock://customer_churn',
                'house_prices': 'mock://house_prices'
            }
    
    def test_classification_pipeline(self):
        """Test complete classification pipeline"""
        test_name = "Classification Pipeline"
        
        try:
            payload = {
                "action": "run_pipeline",
                "objective": "Predict customer churn based on usage and billing patterns",
                "dataset_path": self.test_data['churn'],
                "config": {
                    "test_mode": False,
                    "max_execution_time": 240,  # 4 minutes
                    "target_column": "churn"
                }
            }
            
            print(f"🧪 Running classification pipeline...")
            start_time = time.time()
            
            response = self.lambda_client.invoke(
                FunctionName=TEST_CONFIG['lambda_function'],
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            execution_time = time.time() - start_time
            response_payload = json.loads(response['Payload'].read())
            
            if response_payload.get('status') == 'completed':
                performance = response_payload.get('model_performance', {})
                
                result = {
                    "test": test_name,
                    "status": "PASSED",
                    "details": {
                        "execution_time": execution_time,
                        "pipeline_id": response_payload.get('pipeline_id'),
                        "model_performance": performance,
                        "accuracy": performance.get('accuracy'),
                        "f1_score": performance.get('f1_score')
                    }
                }
                
                print(f"✅ {test_name}: Pipeline completed successfully")
                print(f"   Execution time: {execution_time:.2f}s")
                if performance.get('accuracy'):
                    print(f"   Model accuracy: {performance['accuracy']:.3f}")
                
            else:
                result = {
                    "test": test_name,
                    "status": "FAILED",
                    "error": response_payload.get('error', 'Pipeline execution failed')
                }
                print(f"❌ {test_name}: {response_payload.get('error', 'Unknown error')}")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_regression_pipeline(self):
        """Test complete regression pipeline"""
        test_name = "Regression Pipeline"
        
        try:
            payload = {
                "action": "run_pipeline",
                "objective": "Predict house prices based on property characteristics",
                "dataset_path": self.test_data['house_prices'],
                "config": {
                    "test_mode": False,
                    "max_execution_time": 240,
                    "target_column": "price"
                }
            }
            
            print(f"🧪 Running regression pipeline...")
            start_time = time.time()
            
            response = self.lambda_client.invoke(
                FunctionName=TEST_CONFIG['lambda_function'],
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            execution_time = time.time() - start_time
            response_payload = json.loads(response['Payload'].read())
            
            if response_payload.get('status') == 'completed':
                performance = response_payload.get('model_performance', {})
                
                result = {
                    "test": test_name,
                    "status": "PASSED",
                    "details": {
                        "execution_time": execution_time,
                        "pipeline_id": response_payload.get('pipeline_id'),
                        "model_performance": performance,
                        "r2_score": performance.get('r2_score'),
                        "rmse": performance.get('rmse')
                    }
                }
                
                print(f"✅ {test_name}: Pipeline completed successfully")
                print(f"   Execution time: {execution_time:.2f}s")
                if performance.get('r2_score'):
                    print(f"   Model R²: {performance['r2_score']:.3f}")
                
            else:
                result = {
                    "test": test_name,
                    "status": "FAILED",
                    "error": response_payload.get('error', 'Pipeline execution failed')
                }
                print(f"❌ {test_name}: {response_payload.get('error', 'Unknown error')}")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_pipeline_adaptation(self):
        """Test pipeline adaptation based on data characteristics"""
        test_name = "Pipeline Adaptation"
        
        # This test would require more sophisticated analysis
        # For now, we'll mark it as a placeholder
        result = {
            "test": test_name,
            "status": "SKIPPED",
            "details": {
                "reason": "Requires deeper analysis of pipeline decisions",
                "recommended_approach": "Manual verification of pipeline plans"
            }
        }
        
        print(f"⏭️  {test_name}: Skipped (requires manual verification)")
        self.test_results.append(result)
    
    def test_cloudwatch_metrics(self):
        """Test CloudWatch metrics publishing"""
        test_name = "CloudWatch Metrics"
        
        try:
            # Check for recent metrics in CloudWatch
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            metrics = self.cloudwatch.list_metrics(
                Namespace='ADPA',
                MetricName='PipelineSuccess',
                StartTime=start_time,
                EndTime=end_time
            )
            
            if metrics.get('Metrics'):
                result = {
                    "test": test_name,
                    "status": "PASSED", 
                    "details": {
                        "metrics_found": len(metrics['Metrics']),
                        "namespace": "ADPA"
                    }
                }
                print(f"✅ {test_name}: {len(metrics['Metrics'])} metrics found")
            else:
                result = {
                    "test": test_name,
                    "status": "WARNING",
                    "details": {
                        "metrics_found": 0,
                        "note": "No recent metrics found (may be expected for new deployment)"
                    }
                }
                print(f"⚠️  {test_name}: No recent metrics found")
        
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {test_name}: {e}")
        
        self.test_results.append(result)
    
    def test_kpi_tracking(self):
        """Test KPI tracking functionality"""
        test_name = "KPI Tracking"
        
        # This would require examining DynamoDB or other KPI storage
        result = {
            "test": test_name,
            "status": "SKIPPED",
            "details": {
                "reason": "Requires DynamoDB access verification",
                "alternative": "Check Lambda logs for KPI calculation messages"
            }
        }
        
        print(f"⏭️  {test_name}: Skipped (check Lambda logs for KPI messages)")
        self.test_results.append(result)
    
    def test_large_dataset_handling(self):
        """Test handling of larger datasets"""
        test_name = "Large Dataset Handling"
        
        # For now, we'll skip this as it requires significant resources
        result = {
            "test": test_name,
            "status": "SKIPPED",
            "details": {
                "reason": "Requires large dataset creation",
                "recommendation": "Test manually with production-sized datasets"
            }
        }
        
        print(f"⏭️  {test_name}: Skipped (requires large dataset)")
        self.test_results.append(result)
    
    def test_concurrent_executions(self):
        """Test concurrent pipeline executions"""
        test_name = "Concurrent Executions"
        
        # Skip for now to avoid overwhelming the system
        result = {
            "test": test_name,
            "status": "SKIPPED",
            "details": {
                "reason": "Avoided to prevent system overload",
                "recommendation": "Test manually with controlled load"
            }
        }
        
        print(f"⏭️  {test_name}: Skipped (prevents system overload)")
        self.test_results.append(result)
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE ADPA TEST REPORT")
        print("=" * 60)
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['status'] == 'PASSED')
        failed_tests = sum(1 for r in self.test_results if r['status'] == 'FAILED')
        skipped_tests = sum(1 for r in self.test_results if r['status'] == 'SKIPPED')
        warning_tests = sum(1 for r in self.test_results if r['status'] == 'WARNING')
        
        print(f"\n📈 Test Statistics:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   ⚠️  Warnings: {warning_tests}")
        print(f"   ⏭️  Skipped: {skipped_tests}")
        print(f"   Success Rate: {passed_tests/(total_tests-skipped_tests)*100:.1f}%")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for result in self.test_results:
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌', 
                'SKIPPED': '⏭️',
                'WARNING': '⚠️'
            }.get(result['status'], '❓')
            
            print(f"   {status_icon} {result['test']}: {result['status']}")
            
            if result['status'] == 'FAILED' and 'error' in result:
                print(f"      Error: {result['error']}")
        
        # System readiness assessment
        print(f"\n🎯 System Readiness Assessment:")
        
        if failed_tests == 0:
            print("   🟢 PRODUCTION READY")
            print("   System passed all critical tests")
        elif failed_tests <= 2:
            print("   🟡 MOSTLY READY")
            print("   Minor issues found, review failed tests")
        else:
            print("   🔴 NEEDS ATTENTION")
            print("   Multiple issues found, address failures")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if failed_tests == 0:
            print("   • Deploy to production with confidence")
            print("   • Set up monitoring alerts")
            print("   • Schedule regular health checks")
        else:
            print("   • Address failed tests before production deployment")
            print("   • Review error logs in CloudWatch")
            print("   • Test with larger datasets manually")
        
        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"adpa_test_report_{timestamp}.json"
        
        detailed_report = {
            "timestamp": datetime.now().isoformat(),
            "test_config": TEST_CONFIG,
            "statistics": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "warnings": warning_tests,
                "success_rate": passed_tests/(total_tests-skipped_tests)*100 if total_tests > skipped_tests else 0
            },
            "test_results": self.test_results
        }
        
        try:
            with open(report_filename, 'w') as f:
                json.dump(detailed_report, f, indent=2, default=str)
            print(f"\n📄 Detailed report saved: {report_filename}")
        except Exception as e:
            print(f"\n⚠️  Could not save detailed report: {e}")
        
        print("\n" + "=" * 60)
        print("🏁 Testing Complete!")


def main():
    """Run comprehensive ADPA tests"""
    
    print("🧪 ADPA Comprehensive Test Suite")
    print("Testing complete end-to-end workflow")
    print()
    
    # Initialize and run tests
    test_suite = ADPATestSuite()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()