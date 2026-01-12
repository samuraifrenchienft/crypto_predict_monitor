#!/usr/bin/env python
"""Test dashboard imports for Render deployment"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Testing imports...")
    
    # Test basic imports
    import flask
    from flask import Flask, jsonify
    print("✓ Flask imported")
    
    # Test dashboard imports
    from dashboard.app import app
    print("✓ Dashboard app imported")
    
    # Test if app is callable
    assert callable(app), "app is not callable"
    print("✓ App is callable")
    
    print("\nAll imports successful! Ready for deployment.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
