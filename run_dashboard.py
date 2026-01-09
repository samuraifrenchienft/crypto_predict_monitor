#!/usr/bin/env python
"""
Run the crypto prediction monitor dashboard.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from dashboard.app import app
    app.run(host="0.0.0.0", port=5000, debug=False)
