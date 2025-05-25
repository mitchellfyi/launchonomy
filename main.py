#!/usr/bin/env python3
"""
Main entry point for Launchonomy.

This script provides a convenient way to run the Launchonomy CLI.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from launchonomy.cli import main

if __name__ == "__main__":
    main() 