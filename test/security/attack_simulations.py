"""
Security Testing and Attack Simulation Framework for ADPA

This module provides comprehensive security testing including:
- Penetration testing scenarios
- Injection attack simulations
- Authentication/authorization testing
- DDoS resilience testing
- Data encryption validation
"""

import requests
import boto3
import json
import time
from typing import Dict, Any, List
from datetime import datetime


class SecurityTester:
    """Comprehensive security testing framework"""
    
    def __init__(self, api_endpoint: str, region: str = 'us-east-2'):
        """
        Initialize security tester
        
        Args:
            api_endpoint: API Gateway endpoint URL
            region: AWS region
        """
        self.api_endpoint = api_endpoint
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.test_results = []
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run complete security test suite
        
        Returns:
            Dict containing all test results
        """
        print("🔐 Starting ADPA Security Test Suite")
        print("=" * 50)
        
        # Run all test categories
        self.test_sql_injection()
        self.test_xss_attacks()
        self.test_authentication()
        self.test_rate_limiting()
        self.test_encryption_at_rest()
        self.test_encryption_in_transit()
        self.test_iam_permissions()
        self.test_input_validation()
        
        # Generate summary report
        return self._generate_report()
    
    def test_sql_injection(self) -> None:
        """Test SQL injection attack scenarios"""
        print("\n📌 Testing SQL Injection Protection...")
        
        payloads = [
            "' OR '1'='1",
            "admin'--",
            "1' UNION SELECT NULL--",
            "'; DROP TABLE users--",
            "1' AND '1'='1",
        ]
        
        for payload in payloads:
            try:
                # Attempt injection in pipeline objective
                response = requests.post(
                    f"{self.api_endpoint}/pipelines",
                    json={
                        "objective": payload,
                        "dataset_path": "s3://test/data.csv"
                    },
                    headers={"X-API-Key": "test-key"},
                    timeout=5
                )
                
                # Check if payload was sanitized/blocked
                if response.status_code == 400 or response.status_code == 403:
                    self._log_result("SQL Injection", "PASS", f"Payload blocked: {payload}")
                else:
                    self._log_result("SQL Injection", "FAIL", f"Payload not blocked: {payload}")
            
            except Exception as e:
                self._log_result("SQL Injection", "ERROR", str(e))
    
    def test_xss_attacks(self) -> None:
        """Test Cross-Site Scripting (XSS) protection"""
        print("\n📌 Testing XSS Protection...")
        
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
        ]
        
        for payload in payloads:
            try:
                response = requests.post(
                    f"{self.api_endpoint}/pipelines",
                    json={"objective": payload, "dataset_path": "s3://test/data.csv"},
                    headers={"X-API-Key": "test-key"},
                    timeout=5
                )
                
                # Check if XSS payload is escaped/blocked
                if '<script>' not in response.text:
                    self._log_result("XSS Protection", "PASS", f"Payload escaped: {payload}")
                else:
                    self._log_result("XSS Protection", "FAIL", f"Payload not escaped: {payload}")
            
            except Exception as e:
                self._log_result("XSS Protection", "ERROR", str(e))
    
    def test_authentication(self) -> None:
        """Test authentication and authorization"""
        print("\n📌 Testing Authentication & Authorization...")
        
        # Test without API key
        try:
            response = requests.get(f"{self.api_endpoint}/pipelines", timeout=5)
            
            if response.status_code == 401 or response.status_code == 403:
                self._log_result("Authentication", "PASS", "Unauthorized access blocked")
            else:
                self._log_result("Authentication", "FAIL", "Unauthorized access allowed")
        
        except Exception as e:
            self._log_result("Authentication", "ERROR", str(e))
        
        # Test with invalid API key
        try:
            response = requests.get(
                f"{self.api_endpoint}/pipelines",
                headers={"X-API-Key": "invalid-key-12345"},
                timeout=5
            )
            
            if response.status_code == 401 or response.status_code == 403:
                self._log_result("Authorization", "PASS", "Invalid API key rejected")
            else:
                self._log_result("Authorization", "FAIL", "Invalid API key accepted")
        
        except Exception as e:
            self._log_result("Authorization", "ERROR", str(e))
    
    def test_rate_limiting(self) -> None:
        """Test DDoS protection via rate limiting"""
        print("\n📌 Testing Rate Limiting (DDoS Protection)...")
        
        # Send rapid requests
        success_count = 0
        blocked_count = 0
        
        for i in range(100):
            try:
                response = requests.get(
                    f"{self.api_endpoint}/health",
                    timeout=2
                )
                
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:  # Too Many Requests
                    blocked_count += 1
                
            except Exception:
                pass
        
        if blocked_count > 0:
            self._log_result(
                "Rate Limiting",
                "PASS",
                f"Rate limiting active: {blocked_count}/100 requests blocked"
            )
        else:
            self._log_result(
                "Rate Limiting",
                "WARN",
                f"No rate limiting detected: {success_count}/100 requests succeeded"
            )
    
    def test_encryption_at_rest(self) -> None:
        """Test S3 encryption at rest"""
        print("\n📌 Testing Encryption at Rest...")
        
        buckets = [
            'adpa-data-083308938449-development',
            'adpa-models-083308938449-development'
        ]
        
        for bucket in buckets:
            try:
                # Check bucket encryption
                encryption = self.s3_client.get_bucket_encryption(Bucket=bucket)
                
                rules = encryption.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
                
                if rules:
                    encryption_type = rules[0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
                    self._log_result(
                        "Encryption at Rest",
                        "PASS",
                        f"{bucket}: {encryption_type} encryption enabled"
                    )
                else:
                    self._log_result(
                        "Encryption at Rest",
                        "FAIL",
                        f"{bucket}: No encryption configured"
                    )
            
            except self.s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                self._log_result(
                    "Encryption at Rest",
                    "FAIL",
                    f"{bucket}: No encryption configuration found"
                )
            except Exception as e:
                self._log_result("Encryption at Rest", "ERROR", str(e))
    
    def test_encryption_in_transit(self) -> None:
        """Test HTTPS enforcement"""
        print("\n📌 Testing Encryption in Transit...")
        
        # Test HTTP (should be blocked)
        http_endpoint = self.api_endpoint.replace('https://', 'http://')
        
        try:
            response = requests.get(f"{http_endpoint}/health", timeout=5)
            self._log_result(
                "Encryption in Transit",
                "FAIL",
                "HTTP connection allowed (should enforce HTTPS)"
            )
        except requests.exceptions.SSLError:
            self._log_result(
                "Encryption in Transit",
                "PASS",
                "HTTPS enforced - HTTP connections blocked"
            )
        except Exception as e:
            if "HTTPS" in str(e) or "SSL" in str(e):
                self._log_result("Encryption in Transit", "PASS", "HTTPS enforced")
            else:
                self._log_result("Encryption in Transit", "ERROR", str(e))
    
    def test_iam_permissions(self) -> None:
        """Test IAM role permissions (least privilege)"""
        print("\n📌 Testing IAM Permissions...")
        
        # Check Lambda function role
        try:
            response = self.lambda_client.get_function(
                FunctionName='adpa-data-processor-development'
            )
            
            role_arn = response['Configuration']['Role']
            
            # Verify role has only necessary permissions
            # (In production, you'd parse the role policy)
            self._log_result(
                "IAM Permissions",
                "INFO",
                f"Lambda role: {role_arn.split('/')[-1]}"
            )
        
        except Exception as e:
            self._log_result("IAM Permissions", "ERROR", str(e))
    
    def test_input_validation(self) -> None:
        """Test input validation and sanitization"""
        print("\n📌 Testing Input Validation...")
        
        # Test with oversized payload
        large_payload = "A" * 1000000  # 1MB string
        
        try:
            response = requests.post(
                f"{self.api_endpoint}/pipelines",
                json={"objective": large_payload, "dataset_path": "s3://test/data.csv"},
                headers={"X-API-Key": "test-key"},
                timeout=10
            )
            
            if response.status_code == 413 or response.status_code == 400:
                self._log_result("Input Validation", "PASS", "Large payload rejected")
            else:
                self._log_result("Input Validation", "FAIL", "Large payload accepted")
        
        except Exception as e:
            self._log_result("Input Validation", "ERROR", str(e))
        
        # Test with invalid S3 path
        try:
            response = requests.post(
                f"{self.api_endpoint}/pipelines",
                json={"objective": "test", "dataset_path": "invalid-path"},
                headers={"X-API-Key": "test-key"},
                timeout=5
            )
            
            if response.status_code == 400:
                self._log_result("Input Validation", "PASS", "Invalid S3 path rejected")
            else:
                self._log_result("Input Validation", "WARN", "Invalid S3 path not validated")
        
        except Exception as e:
            self._log_result("Input Validation", "ERROR", str(e))
    
    def _log_result(self, test_category: str, status: str, message: str) -> None:
        """Log test result"""
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": test_category,
            "status": status,
            "message": message
        }
        self.test_results.append(result)
        
        # Print with color coding
        status_symbols = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️",
            "ERROR": "🔥",
            "INFO": "ℹ️"
        }
        
        symbol = status_symbols.get(status, "•")
        print(f"  {symbol} [{status}] {message}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate security test report"""
        total_tests = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.test_results if r['status'] == 'WARN')
        errors = sum(1 for r in self.test_results if r['status'] == 'ERROR')
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "errors": errors,
                "pass_rate": round((passed / total_tests) * 100, 2) if total_tests > 0 else 0
            },
            "details": self.test_results,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Print summary
        print("\n" + "=" * 50)
        print("🔐 Security Test Summary")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"🔥 Errors: {errors}")
        print(f"Pass Rate: {report['summary']['pass_rate']}%")
        print("=" * 50)
        
        return report


# CLI usage
if __name__ == "__main__":
    # Replace with your actual API Gateway endpoint
    API_ENDPOINT = "https://your-api-id.execute-api.us-east-2.amazonaws.com/v1"
    
    tester = SecurityTester(API_ENDPOINT)
    report = tester.run_all_tests()
    
    # Save report
    with open('security_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved to security_test_report.json")
