# Python version check: 3.11-3.13
import sys
import os
from pathlib import Path

# Import metadata
from app.config import WORKSPACE_ROOT

# Create necessary directories
os.makedirs(WORKSPACE_ROOT, exist_ok=True)

# Expose version information
__version__ = "0.1.0"
__author__ = "OpenManus Contributors"
__license__ = "MIT"

if sys.version_info < (3, 11) or sys.version_info > (3, 13):
    print(
        "Warning: Unsupported Python version {ver}, please use 3.11-3.13".format(
            ver=".".join(map(str, sys.version_info))
        )
    )
