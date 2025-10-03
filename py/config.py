"""
Shim to expose `Config` from the existing file named 'Configuration Module.py'.

Keeps original filenames intact while allowing clean imports like `from config import Config`.
"""
from __future__ import annotations
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
orig = HERE / "Configuration Module.py"

if not orig.exists():
    raise FileNotFoundError(f"Expected configuration file not found: {orig}")

spec = importlib.util.spec_from_file_location("_config_original", str(orig))
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

try:
    Config = getattr(mod, "Config")
except AttributeError:
    raise AttributeError("Could not find 'Config' in 'Configuration Module.py'. Open the file and check the class name.")

__all__ = ["Config"]
