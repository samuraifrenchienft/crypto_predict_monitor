#!/usr/bin/env python3
"""
Staging Deployment Script for Crypto Predict Monitor
Deploys and configures the application in a staging environment
"""

import os
import sys
import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StagingDeployer:
    """Handles staging deployment operations"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_file = project_root / "config" / "staging.env"
        self.health_checks = [
            "http://localhost:8000/health",
            "http://localhost:8000/api/pnl-card/health"
        ]
        
    def load_config(self) -> Dict[str, str]:
        """Load staging configuration"""
        config = {}
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        else:
            logger.warning(f"Config file {self.config_file} not found")
        return config
    
    def set_environment(self, config: Dict[str, str]) -> None:
        """Set environment variables from config"""
        for key, value in config.items():
            os.environ[key] = value
        logger.info(f"Loaded {len(config)} environment variables")
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        logger.info("Checking dependencies...")
        
        # Check Python
        try:
            result = subprocess.run([sys.executable, "--version"], 
                                  capture_output=True, text=True)
            logger.info(f"Python: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Python not found")
            return False
        
        # Check Node.js (for frontend)
        try:
            result = subprocess.run(["node", "--version"], 
                                  capture_output=True, text=True)
            logger.info(f"Node.js: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.warning("Node.js not found - frontend deployment skipped")
        
        # Check if required files exist
        required_files = [
            "src/main.py",
            "src/main_enhanced.py",
            "simple_backend.py",
            "requirements.txt"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            return False
        
        logger.info("All dependencies satisfied")
        return True
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")
        
        try:
            # Install main requirements
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                "requirements.txt"
            ], check=True, cwd=self.project_root)
            
            # Install P&L requirements
            pnl_req = self.project_root / "pnl_requirements.txt"
            if pnl_req.exists():
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", 
                    "pnl_requirements.txt"
                ], check=True, cwd=self.project_root)
            
            logger.info("Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def run_database_migrations(self) -> bool:
        """Run database migrations"""
        logger.info("Running database migrations...")
        
        try:
            result = subprocess.run([
                sys.executable, "-c",
                "from src.database.migrate import run_supabase_migrations; "
                "run_supabase_migrations()"
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Database migrations completed successfully")
                return True
            else:
                logger.error(f"Migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False
    
    def start_backend(self) -> bool:
        """Start the backend application"""
        logger.info("Starting backend application...")
        
        try:
            # Start backend in background
            process = subprocess.Popen([
                sys.executable, "-m", "src.main_enhanced.py"
            ], cwd=self.project_root)
            
            # Wait a bit for startup
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info("Backend started successfully (PID: {process.pid})")
                self.backend_process = process
                return True
            else:
                logger.error("Backend failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            return False
    
    def start_dashboard(self) -> bool:
        """Start the web dashboard"""
        logger.info("Starting web dashboard...")
        
        dashboard_script = self.project_root / "run_dashboard.py"
        if not dashboard_script.exists():
            logger.warning("Dashboard script not found")
            return False
        
        try:
            process = subprocess.Popen([
                sys.executable, str(dashboard_script)
            ], cwd=self.project_root)
            
            time.sleep(3)
            
            if process.poll() is None:
                logger.info("Dashboard started successfully (PID: {process.pid})")
                self.dashboard_process = process
                return True
            else:
                logger.error("Dashboard failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            return False
    
    def health_check(self) -> bool:
        """Perform health checks on deployed services"""
        logger.info("Performing health checks...")
        
        import requests
        
        for url in self.health_checks:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✓ {url}")
                else:
                    logger.error(f"✗ {url} - Status: {response.status_code}")
                    return False
            except requests.RequestException as e:
                logger.error(f"✗ {url} - Error: {e}")
                return False
        
        logger.info("All health checks passed")
        return True
    
    def run_tests(self) -> bool:
        """Run basic tests to validate deployment"""
        logger.info("Running deployment tests...")
        
        test_files = [
            "test_api_comprehensive.py",
            "test_backend_unit.py"
        ]
        
        for test_file in test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                try:
                    result = subprocess.run([
                        sys.executable, str(test_path)
                    ], cwd=self.project_root, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"✓ {test_file}")
                    else:
                        logger.error(f"✗ {test_file} - {result.stderr}")
                        return False
                        
                except Exception as e:
                    logger.error(f"✗ {test_file} - Error: {e}")
                    return False
        
        logger.info("All tests passed")
        return True
    
    def deploy(self) -> bool:
        """Execute the full deployment process"""
        logger.info("Starting staging deployment...")
        
        # Load configuration
        config = self.load_config()
        self.set_environment(config)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Install dependencies
        if not self.install_dependencies():
            return False
        
        # Run migrations
        if not self.run_database_migrations():
            return False
        
        # Start services
        if not self.start_backend():
            return False
        
        if not self.start_dashboard():
            logger.warning("Dashboard failed to start, continuing...")
        
        # Wait for services to be ready
        logger.info("Waiting for services to be ready...")
        time.sleep(10)
        
        # Health checks
        if not self.health_check():
            logger.error("Health checks failed")
            return False
        
        # Run tests
        if not self.run_tests():
            logger.warning("Some tests failed, deployment may be incomplete")
        
        logger.info("Staging deployment completed successfully!")
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        
        if hasattr(self, 'backend_process'):
            self.backend_process.terminate()
        
        if hasattr(self, 'dashboard_process'):
            self.dashboard_process.terminate()

def main():
    """Main deployment function"""
    project_root = Path(__file__).parent.parent
    
    deployer = StagingDeployer(project_root)
    
    try:
        success = deployer.deploy()
        if success:
            print("\n🚀 Staging deployment completed successfully!")
            print("\nService URLs:")
            print("  Backend API:  http://localhost:8000")
            print("  Dashboard:    http://localhost:3000")
            print("  Health Check: http://localhost:8000/health")
            sys.exit(0)
        else:
            print("\n❌ Staging deployment failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Deployment interrupted")
        deployer.cleanup()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        deployer.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
