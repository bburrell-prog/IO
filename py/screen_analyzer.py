"""
Shim module to expose `ScreenAnalyzer` under the import name `screen_analyzer`.

This loads the original file named "Screen Analyzer Module.py" (which contains spaces)
using importlib so `from screen_analyzer import ScreenAnalyzer` works without renaming.

If you later rename the original file to `screen_analyzer.py`, this shim can be removed.
"""
from __future__ import annotations
import importlib.util
import pathlib
import sys
from typing import Any, Dict

# Import the new universal vision processor
try:
    from vision_processor import UniversalVisionProcessor
except Exception:
    UniversalVisionProcessor = None

HERE = pathlib.Path(__file__).resolve().parent
orig_path = HERE / "Screen Analyzer Module.py"

if not orig_path.exists():
    raise FileNotFoundError(f"Expected file not found: {orig_path}")

spec = importlib.util.spec_from_file_location("_screen_analyzer_original", str(orig_path))
module = importlib.util.module_from_spec(spec)
# Ensure module is available on sys.modules in case the original module expects to import relative names
sys.modules[spec.name] = module
orig_loaded = False
try:
    spec.loader.exec_module(module)
    orig_loaded = True
except Exception as e:
    import logging
    logging.exception("Failed to import original Screen Analyzer Module: %s", e)

# Export the expected symbol(s) used by Main Application.py
if orig_loaded:
    try:
        _orig_class = getattr(module, "ScreenAnalyzer")
    except AttributeError:
        raise AttributeError(
            "Could not find 'ScreenAnalyzer' in 'Screen Analyzer Module.py'. Open that file and confirm the class name."
        )

    # Wrap the original to add CV processing. Use _orig_class inside the wrapper to
    # avoid calling the re-bound name (ScreenAnalyzer) which would cause recursion.
    class _WrappedScreenAnalyzer:
        def __init__(self, *args, **kwargs):
            # instantiate the real original analyzer class
            self._orig = _orig_class(*args, **kwargs)
            self._cv = UniversalVisionProcessor() if UniversalVisionProcessor is not None else None

        def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
            # call original analyzer
            base = {}
            try:
                base = self._orig.analyze_screenshot(screenshot_path) or {}
            except Exception:
                import logging
                logging.exception("Original ScreenAnalyzer.analyze_screenshot failed; falling back to CV-only processing.")

            # call new vision processor and merge
            if self._cv is not None:
                try:
                    cv_out = self._cv.process_image(screenshot_path) or {}
                    merged = dict(base)
                    merged.setdefault("cv_analysis", {})
                    merged["cv_analysis"].update(cv_out)
                    return merged
                except Exception:
                    logging.exception("VisionProcessor failed while analyzing %s", screenshot_path)
                    return base

            return base

        def __getattr__(self, name: str):
            """Proxy any unknown attribute access to the original analyzer instance.

            This covers methods like `capture_screenshot` that the original module
            provides but the wrapper doesn't explicitly implement.
            """
            return getattr(self._orig, name)

    ScreenAnalyzer = _WrappedScreenAnalyzer
else:
    # Could not import original analyzer; provide a minimal analyzer that uses vision_processor only
    class _FallbackScreenAnalyzer:
        def __init__(self, *args, **kwargs):
            self._cv = UniversalVisionProcessor() if UniversalVisionProcessor is not None else None

        def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
            if self._cv is None:
                raise RuntimeError("No vision processor available to analyze screenshots")
            return {"cv_analysis": self._cv.process_image(screenshot_path)}

        def analyze_screen(self, screenshot_path: str) -> Dict[str, Any]:
            """Alias for analyze_screenshot for compatibility."""
            return self.analyze_screenshot(screenshot_path)

        def capture_screenshot(self) -> str:
            """Capture a screenshot to the screenshots/ folder and return its path.

            Uses pyautogui if available, otherwise raises RuntimeError.
            """
            try:
                import pyautogui
            except Exception:
                pyautogui = None

            screenshots_dir = "screenshots"
            from pathlib import Path
            Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            dest = Path(screenshots_dir) / filename
            if pyautogui is not None:
                img = pyautogui.screenshot()
                img.save(dest)
                return str(dest)
            raise RuntimeError("No screenshot backend available (pyautogui required for fallback capture)")

    ScreenAnalyzer = _FallbackScreenAnalyzer

__all__ = ["ScreenAnalyzer"]
