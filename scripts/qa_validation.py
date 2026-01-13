#!/usr/bin/env python3
"""
QA Validation Script for Crypto Predict Monitor
Comprehensive testing and validation before release
"""

import os
import sys
import subprocess
import json
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str
    duration: float = 0.0

class QAValidator:
    """Comprehensive QA validation suite"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results: List[TestResult] = []
        self.base_url = "http://localhost:8000"
        self.dashboard_url = "http://localhost:3000"
        
    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and capture results"""
        logger.info(f"Running test: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            if result:
                test_result = TestResult(test_name, TestStatus.PASS, "Test passed", duration)
                logger.info(f"✓ {test_name} - PASS")
            else:
                test_result = TestResult(test_name, TestStatus.FAIL, "Test failed", duration)
                logger.error(f"✗ {test_name} - FAIL")
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(test_name, TestStatus.FAIL, str(e), duration)
            logger.error(f"✗ {test_name} - ERROR: {e}")
        
        self.test_results.append(test_result)
        return test_result
    
    def test_code_quality(self) -> bool:
        """Test code quality and standards"""
        logger.info("Testing code quality...")
        
        # Check for Python syntax errors
        python_files = list(self.project_root.glob("src/**/*.py"))
        python_files.extend(self.project_root.glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(py_file), 'exec')
            except SyntaxError as e:
                logger.error(f"Syntax error in {py_file}: {e}")
                return False
            except UnicodeDecodeError:
                logger.warning(f"Encoding issue in {py_file}, skipping")
                continue
        
        # Check for required files
        required_files = [
            "src/main.py",
            "src/main_enhanced.py", 
            "simple_backend.py",
            "requirements.txt",
            "README.md"
        ]
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                logger.error(f"Required file missing: {file_path}")
                return False
        
        return True
    
    def test_dependencies(self) -> bool:
        """Test that all dependencies are properly installed"""
        logger.info("Testing dependencies...")
        
        try:
            # Test main imports
            import flask
            import requests
            import pydantic
            import sqlalchemy
            logger.info("Core dependencies available")
            
            # Test P&L specific imports
            try:
                import supabase
                import PIL
                logger.info("P&L dependencies available")
            except ImportError as e:
                logger.warning(f"P&L dependency missing: {e}")
            
            return True
            
        except ImportError as e:
            logger.error(f"Missing core dependency: {e}")
            return False
    
    def test_configuration(self) -> bool:
        """Test configuration files and environment"""
        logger.info("Testing configuration...")
        
        # Check config files exist
        config_files = [
            "config/staging.env",
            "config/production.env"
        ]
        
        for config_file in config_files:
            if not (self.project_root / config_file).exists():
                logger.warning(f"Config file missing: {config_file}")
        
        # Test environment variable loading
        try:
            # Add project root to Python path
            sys.path.insert(0, str(self.project_root))
            from src.config import load_settings
            settings = load_settings()
            logger.info("Configuration loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test API endpoints (if server is running)"""
        logger.info("Testing API endpoints...")
        
        endpoints = [
            "/health",
            "/api/pnl-card/health"
        ]
        
        all_passed = True
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    logger.info(f"✓ {endpoint} - {response.status_code}")
                else:
                    logger.warning(f"⚠ {endpoint} - {response.status_code}")
                    all_passed = False
            except requests.RequestException:
                logger.warning(f"⚠ {endpoint} - Connection failed")
                all_passed = False
        
        return all_passed
    
    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        logger.info("Testing database connection...")
        
        try:
            # Test database import
            from src.database.supabase_adapter import SupabaseAdapter
            
            # Try to create adapter (will fail if no connection, but validates code)
            adapter = SupabaseAdapter()
            logger.info("Database adapter created successfully")
            
            # Note: Actual connection test requires database to be running
            return True
            
        except ImportError as e:
            logger.warning(f"Database module not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            return False
    
    def test_pnl_system(self) -> bool:
        """Test P&L card system"""
        logger.info("Testing P&L system...")
        
        try:
            from src.social.pnl_card_generator import PnLCardService
            
            # Test service creation
            service = PnLCardService()
            logger.info("P&L Card Service created successfully")
            
            # Test basic functionality (without actual generation)
            return True
            
        except ImportError as e:
            logger.warning(f"P&L system not available: {e}")
            return False
        except Exception as e:
            logger.error(f"P&L system test failed: {e}")
            return False
    
    def test_security(self) -> bool:
        """Test security configurations"""
        logger.info("Testing security configurations...")
        
        security_checks = []
        
        # Check for hardcoded secrets (basic check)
        sensitive_files = [
            "src/main.py",
            "simple_backend.py",
            "src/config.py"
        ]
        
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()
                    # Check for potential hardcoded secrets
                    if 'password' in content.lower() and '=' in content:
                        logger.warning(f"Potential hardcoded password in {file_path}")
                        security_checks.append(False)
                    else:
                        security_checks.append(True)
        
        # Check .gitignore for sensitive files
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
                if '.env' in gitignore_content:
                    security_checks.append(True)
                else:
                    logger.warning(".env not in .gitignore")
                    security_checks.append(False)
        
        return all(security_checks)
    
    def test_documentation(self) -> bool:
        """Test documentation completeness"""
        logger.info("Testing documentation...")
        
        required_docs = [
            "README.md",
            "docs/api.md"
        ]
        
        missing_docs = []
        for doc in required_docs:
            if not (self.project_root / doc).exists():
                missing_docs.append(doc)
        
        if missing_docs:
            logger.warning(f"Missing documentation: {missing_docs}")
            return False
        
        return True
    
    def test_docker_setup(self) -> bool:
        """Test Docker configuration"""
        logger.info("Testing Docker setup...")
        
        docker_files = [
            "Dockerfile",
            "Dockerfile.prod",
            "Dockerfile.dashboard",
            "docker-compose.yml",
            "docker-compose.prod.yml"
        ]
        
        docker_checks = []
        for docker_file in docker_files:
            if (self.project_root / docker_file).exists():
                docker_checks.append(True)
            else:
                logger.warning(f"Docker file missing: {docker_file}")
                docker_checks.append(False)
        
        return all(docker_checks)
    
    def test_performance(self) -> bool:
        """Basic performance tests"""
        logger.info("Testing performance...")
        
        try:
            # Test import performance
            start_time = time.time()
            from src.main import main
            import_time = time.time() - start_time
            
            if import_time > 5.0:  # 5 second threshold
                logger.warning(f"Slow import time: {import_time:.2f}s")
                return False
            
            logger.info(f"Import performance: {import_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, TestResult]:
        """Run all QA tests"""
        logger.info("Starting comprehensive QA validation...")
        
        tests = [
            ("Code Quality", self.test_code_quality),
            ("Dependencies", self.test_dependencies),
            ("Configuration", self.test_configuration),
            ("API Endpoints", self.test_api_endpoints),
            ("Database Connection", self.test_database_connection),
            ("P&L System", self.test_pnl_system),
            ("Security", self.test_security),
            ("Documentation", self.test_documentation),
            ("Docker Setup", self.test_docker_setup),
            ("Performance", self.test_performance)
        ]
        
        results = {}
        for test_name, test_func in tests:
            result = self.run_test(test_name, test_func)
            results[test_name] = result
        
        return results
    
    def generate_report(self) -> str:
        """Generate QA validation report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.status == TestStatus.PASS)
        failed_tests = sum(1 for r in self.test_results if r.status == TestStatus.FAIL)
        skipped_tests = sum(1 for r in self.test_results if r.status == TestStatus.SKIP)
        
        total_duration = sum(r.duration for r in self.test_results)
        
        report = f"""
# QA Validation Report

## Summary
- **Total Tests**: {total_tests}
- **Passed**: {passed_tests} ✅
- **Failed**: {failed_tests} ❌
- **Skipped**: {skipped_tests} ⏭️
- **Success Rate**: {(passed_tests/total_tests)*100:.1f}%
- **Total Duration**: {total_duration:.2f}s

## Test Results

"""
        
        for result in self.test_results:
            status_icon = {
                TestStatus.PASS: "✅",
                TestStatus.FAIL: "❌", 
                TestStatus.SKIP: "⏭️"
            }.get(result.status, "❓")
            
            report += f"### {status_icon} {result.name}\n"
            report += f"- **Status**: {result.status.value}\n"
            report += f"- **Duration**: {result.duration:.2f}s\n"
            report += f"- **Message**: {result.message}\n\n"
        
        # Recommendations
        if failed_tests > 0:
            report += "## Recommendations\n\n"
            report += "⚠️ **Failed tests detected**. Please review and fix the following issues before release:\n\n"
            
            failed_results = [r for r in self.test_results if r.status == TestStatus.FAIL]
            for result in failed_results:
                report += f"- **{result.name}**: {result.message}\n"
        
        # Overall status
        if failed_tests == 0:
            report += "\n## 🎉 Overall Status: READY FOR RELEASE\n"
            report += "All tests passed. The system is ready for production deployment.\n"
        else:
            report += f"\n## ⚠️ Overall Status: NOT READY\n"
            report += f"{failed_tests} test(s) failed. Address issues before release.\n"
        
        return report
    
    def save_report(self, report: str) -> None:
        """Save QA report to file"""
        report_file = self.project_root / "qa_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"QA report saved to {report_file}")

def main():
    """Main QA validation function"""
    project_root = Path(__file__).parent.parent
    
    validator = QAValidator(project_root)
    
    try:
        # Run all tests
        results = validator.run_all_tests()
        
        # Generate and save report
        report = validator.generate_report()
        validator.save_report(report)
        
        # Print summary
        print("\n" + "="*50)
        print("QA VALIDATION COMPLETE")
        print("="*50)
        
        passed = sum(1 for r in validator.test_results if r.status == TestStatus.PASS)
        total = len(validator.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Report saved to: qa_report.md")
        
        if passed == total:
            print("\n🎉 READY FOR RELEASE!")
            return 0
        else:
            print(f"\n⚠️ {total-passed} TESTS FAILED - Review required")
            return 1
            
    except Exception as e:
        logger.error(f"QA validation error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
