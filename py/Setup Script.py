#!/usr/bin/env python3
"""
Setup script for the Desktop Screen Analyzer.
This script checks for dependencies and helps with initial configuration.
"""
import os
import sys
import subprocess
import platform
import shutil

def check_python_version():
    """Checks if the current Python version is 3.8+."""
    print("1. Checking Python version...")
    if sys.version_info < (3, 8):
        print(f"❌ Error: Python 3.8 or higher is required. You are using {platform.python_version()}.")
        return False
    print(f"✅ Python version {platform.python_version()} is compatible.")
    return True

def check_tesseract():
    """Checks if Tesseract OCR is installed and accessible in the system's PATH."""
    print("\n2. Checking for Tesseract OCR installation...")
    if shutil.which("tesseract"):
        print("✅ Tesseract OCR found.")
        return True
    else:
        print("❌ Warning: Tesseract OCR is not found in your system's PATH.")
        print("   Please install it and ensure it's in your PATH.")
        print("   - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   - macOS (via Homebrew): brew install tesseract")
        print("   - Linux (Ubuntu/Debian): sudo apt-get install tesseract-ocr")
        return False

def install_dependencies():
    """Installs required Python packages from requirements.txt."""
    print("\n3. Installing Python dependencies from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_env_file():
    """Creates the .env file from .env.example if it doesn't exist."""
    print("\n4. Creating .env configuration file...")
    if os.path.exists('.env'):
        print("✅ .env file already exists.")
    elif os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
        print("✅ .env file created from .env.example.")
        print("   IMPORTANT: You must now edit the .env file and add your OPENAI_API_KEY.")
    else:
        print("❌ Warning: .env.example not found. Could not create .env file.")

def main():
    """Runs the complete setup process."""
    print("--- Desktop Screen Analyzer Setup ---")
    if not check_python_version():
        sys.exit(1)
    
    if not check_tesseract():
        if input("Continue anyway? (y/n): ").lower() != 'y':
            sys.exit(1)

    if not install_dependencies():
        sys.exit(1)

    create_env_file()
    
    print("\n--- Setup Complete! ---")
    print("\nNext Steps:")
    print("1. IMPORTANT: Edit the '.env' file and add your OpenAI API key.")
    print("2. Run the application with: python main.py")
    print("3. In interactive mode, press F9 to start an analysis.")
    print("\nSee README.md for more details.")

if __name__ == "__main__":
    main()

