#!/usr/bin/env python3
"""
Test helper to set up paths and environment for testing
"""
import sys
import os
from pathlib import Path

def setup_backend_environment():
    """Set up backend path and working directory for tests"""
    backend_path = Path(__file__).parent.parent / 'backend'
    sys.path.insert(0, str(backend_path))
    os.chdir(str(backend_path))
    return backend_path