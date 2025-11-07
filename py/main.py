#!/usr/bin/env python3
"""
Main entry point for the Desktop Screen Analyzer.
This file provides a clean import from 'Main Application.py' with spaces in the name.
"""
import sys
import importlib.util
from pathlib import Path

# Import the main application from the file with spaces in its name
main_app_path = Path(__file__).parent / "Main Application.py"

if not main_app_path.exists():
    print(f"Error: Could not find 'Main Application.py' at {main_app_path}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("main_application", str(main_app_path))
main_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = main_module
spec.loader.exec_module(main_module)

# Run the main function
if __name__ == "__main__":
    main_module.main()
