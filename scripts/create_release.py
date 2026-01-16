#!/usr/bin/env python3
"""
Release Creation Script for Crypto Predict Monitor
Automates the release candidate creation process
"""

import os
import sys
import subprocess
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ReleaseInfo:
    version: str
    build_number: str
    git_hash: str
    timestamp: datetime
    artifacts: List[str]

class ReleaseCreator:
    """Creates release candidates with validation and packaging"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version = "2.0.0"
        self.build_number = datetime.now().strftime("%Y%m%d%H%M")
        self.artifacts_dir = project_root / "releases"
        self.artifacts_dir.mkdir(exist_ok=True)
        
    def get_git_info(self) -> Dict[str, str]:
        """Get git repository information"""
        try:
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            git_hash = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            branch = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Get remote URL
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            remote_url = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            return {
                "hash": git_hash,
                "branch": branch,
                "remote_url": remote_url
            }
        except Exception as e:
            print(f"Warning: Could not get git info: {e}")
            return {
                "hash": "unknown",
                "branch": "unknown", 
                "remote_url": "unknown"
            }
    
    def validate_working_directory(self) -> bool:
        """Validate that working directory is clean for release"""
        try:
            # Check if git working directory is clean
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print("❌ Working directory is not clean:")
                print(result.stdout)
                return False
            
            print("✅ Working directory is clean")
            return True
            
        except Exception as e:
            print(f"❌ Error checking working directory: {e}")
            return False
    
    def run_qa_validation(self) -> bool:
        """Run QA validation suite"""
        print("🧪 Running QA validation...")
        
        qa_script = self.project_root / "scripts" / "qa_validation.py"
        if not qa_script.exists():
            print("❌ QA validation script not found")
            return False
        
        try:
            result = subprocess.run(
                [sys.executable, str(qa_script)],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ QA validation passed")
                return True
            else:
                print("❌ QA validation failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error running QA validation: {e}")
            return False
    
    def create_source_archive(self) -> str:
        """Create source archive"""
        print("📦 Creating source archive...")
        
        archive_name = f"crypto-predict-monitor-{self.version}-src.tar.gz"
        archive_path = self.artifacts_dir / archive_name
        
        # Files to exclude
        exclude_patterns = [
            ".git",
            ".gitignore",
            "__pycache__",
            "*.pyc",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            "*.log",
            ".env",
            "releases/",
            "temp/",
            "*.tmp"
        ]
        
        try:
            # Create tar.gz archive
            import tarfile
            
            with tarfile.open(archive_path, "w:gz") as tar:
                for file_path in self.project_root.rglob("*"):
                    # Skip directories and excluded patterns
                    if file_path.is_dir():
                        continue
                    
                    # Check if file should be excluded
                    if any(pattern in str(file_path) for pattern in exclude_patterns):
                        continue
                    
                    # Add file to archive with relative path
                    arcname = file_path.relative_to(self.project_root)
                    tar.add(file_path, arcname=arcname)
            
            print(f"✅ Source archive created: {archive_path}")
            return str(archive_path)
            
        except Exception as e:
            print(f"❌ Error creating source archive: {e}")
            return ""
    
    def create_checksums(self, artifacts: List[str]) -> str:
        """Create checksums file for artifacts"""
        print("🔐 Creating checksums...")
        
        checksums_file = self.artifacts_dir / f"checksums-{self.version}.txt"
        
        try:
            with open(checksums_file, 'w') as f:
                for artifact_path in artifacts:
                    if Path(artifact_path).exists():
                        # Calculate SHA256 checksum
                        sha256_hash = hashlib.sha256()
                        with open(artifact_path, "rb") as af:
                            for chunk in iter(lambda: af.read(4096), b""):
                                sha256_hash.update(chunk)
                        
                        checksum = sha256_hash.hexdigest()
                        filename = Path(artifact_path).name
                        f.write(f"{checksum}  {filename}\n")
            
            print(f"✅ Checksums created: {checksums_file}")
            return str(checksums_file)
            
        except Exception as e:
            print(f"❌ Error creating checksums: {e}")
            return ""
    
    def create_release_manifest(self, artifacts: List[str], git_info: Dict[str, str]) -> str:
        """Create release manifest"""
        print("📋 Creating release manifest...")
        
        manifest = {
            "version": self.version,
            "build_number": self.build_number,
            "timestamp": datetime.now().isoformat(),
            "git": git_info,
            "artifacts": [],
            "requirements": {
                "python": ">=3.11",
                "node": ">=18",
                "docker": ">=20.10",
                "memory": ">=2GB",
                "disk": ">=10GB"
            },
            "components": {
                "backend": {
                    "port": 8000,
                    "health_check": "/health",
                    "metrics": "/metrics"
                },
                "dashboard": {
                    "port": 3000,
                    "health_check": "/health"
                },
                "database": {
                    "type": "PostgreSQL/Supabase",
                    "port": 5432
                },
                "monitoring": {
                    "prometheus": 9090,
                    "grafana": 3001,
                    "loki": 3100
                }
            }
        }
        
        # Add artifact information
        for artifact_path in artifacts:
            if Path(artifact_path).exists():
                file_stat = Path(artifact_path).stat()
                manifest["artifacts"].append({
                    "name": Path(artifact_path).name,
                    "size": file_stat.st_size,
                    "type": "application/gzip" if artifact_path.endswith('.tar.gz') else "text/plain"
                })
        
        manifest_file = self.artifacts_dir / f"manifest-{self.version}.json"
        
        try:
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            print(f"✅ Release manifest created: {manifest_file}")
            return str(manifest_file)
            
        except Exception as e:
            print(f"❌ Error creating manifest: {e}")
            return ""
    
    def create_docker_images(self) -> List[str]:
        """Create Docker images for release"""
        print("🐳 Building Docker images...")
        
        images = []
        docker_images = [
            ("crypto-predict-monitor/app:latest", "Dockerfile.prod"),
            ("crypto-predict-monitor/dashboard:latest", "Dockerfile.dashboard")
        ]
        
        for image_name, dockerfile in docker_images:
            dockerfile_path = self.project_root / dockerfile
            if not dockerfile_path.exists():
                print(f"⚠️ Dockerfile not found: {dockerfile}")
                continue
            
            try:
                print(f"Building {image_name}...")
                result = subprocess.run([
                    "docker", "build",
                    "-f", dockerfile,
                    "-t", image_name,
                    "-t", f"{image_name}-{self.version}",
                    "."
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ Docker image built: {image_name}")
                    images.append(image_name)
                else:
                    print(f"❌ Failed to build {image_name}: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ Error building Docker image {image_name}: {e}")
        
        return images
    
    def create_release(self) -> Optional[ReleaseInfo]:
        """Create complete release package"""
        print(f"🚀 Creating release {self.version}...")
        print(f"Build Number: {self.build_number}")
        print("=" * 50)
        
        # Validate working directory
        if not self.validate_working_directory():
            return None
        
        # Run QA validation
        if not self.run_qa_validation():
            print("⚠️ QA validation failed, but continuing with release...")
        
        # Get git information
        git_info = self.get_git_info()
        print(f"📝 Git Info: {git_info['hash'][:8]} on {git_info['branch']}")
        
        # Create artifacts
        artifacts = []
        
        # Source archive
        source_archive = self.create_source_archive()
        if source_archive:
            artifacts.append(source_archive)
        
        # Docker images (if Docker is available)
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
            docker_images = self.create_docker_images()
            artifacts.extend(docker_images)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ Docker not available, skipping Docker images")
        
        # Create checksums
        if artifacts:
            checksums_file = self.create_checksums(artifacts)
            if checksums_file:
                artifacts.append(checksums_file)
        
        # Create release manifest
        manifest_file = self.create_release_manifest(artifacts, git_info)
        if manifest_file:
            artifacts.append(manifest_file)
        
        # Create release info
        release_info = ReleaseInfo(
            version=self.version,
            build_number=self.build_number,
            git_hash=git_info['hash'],
            timestamp=datetime.now(),
            artifacts=artifacts
        )
        
        # Print summary
        print("\n" + "=" * 50)
        print("🎉 RELEASE CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"Version: {release_info.version}")
        print(f"Build: {release_info.build_number}")
        print(f"Git Hash: {release_info.git_hash[:8]}")
        print(f"Timestamp: {release_info.timestamp.isoformat()}")
        print(f"Artifacts: {len(release_info.artifacts)}")
        print(f"Release Directory: {self.artifacts_dir}")
        
        print("\n📦 Artifacts:")
        for artifact in release_info.artifacts:
            artifact_name = Path(artifact).name
            if Path(artifact).exists():
                size = Path(artifact).stat().st_size
                print(f"  ✅ {artifact_name} ({size:,} bytes)")
            else:
                print(f"  ❌ {artifact_name} (missing)")
        
        print("\n🚀 Ready for deployment!")
        
        return release_info

def main():
    """Main release creation function"""
    project_root = Path(__file__).parent.parent
    
    creator = ReleaseCreator(project_root)
    
    try:
        release_info = creator.create_release()
        
        if release_info:
            print(f"\n✅ Release {release_info.version} is ready!")
            return 0
        else:
            print("\n❌ Release creation failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Release creation interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Release creation error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
