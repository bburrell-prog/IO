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
import importlib

SHOW_DEBUG_WINDOWS = False  # Set to True to enable debug windows

# Load optional packages dynamically so static analyzers won't report
# unresolved-import errors when those packages aren't installed in the
# environment running the editor/tooling. At runtime we still detect
# absence and skip CV-based functionality.
def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None

cv2 = _try_import("cv2")
np = _try_import("numpy")

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
            import logging
            logging.info("Wrapped ScreenAnalyzer.analyze_screenshot start: %s", screenshot_path)

            # prepare base/result variables
            base: Dict[str, Any] = {}
            result: Dict[str, Any] = {}

            try:
                # call original analyzer (errors are logged but do not stop flow)
                try:
                    base = self._orig.analyze_screenshot(screenshot_path) or {}
                except Exception:
                    logging.exception("Original ScreenAnalyzer.analyze_screenshot failed; falling back to CV-only processing.")

                # call new vision processor and merge
                result = dict(base)
                if self._cv is not None:
                    try:
                        cv_out = self._cv.process_image(screenshot_path) or {}
                        if cv_out:
                            result.setdefault("cv_analysis", {})
                            result["cv_analysis"].update(cv_out)
                    except Exception:
                        logging.exception("Vision processor failed for %s", screenshot_path)
            finally:
                # Compute and display HSV statistics regardless of earlier errors
                try:
                    self._compute_and_display_hsv_stats(screenshot_path)
                except Exception:
                    logging.exception("Failed to compute HSV stats while finalizing analysis for %s", screenshot_path)

            return result
        def _compute_and_display_hsv_stats(self, screenshot_path: str):
            import logging
            try:
                logging.info("Computing HSV stats for %s", screenshot_path)
                if cv2 is not None and np is not None:
                    img = cv2.imread(screenshot_path)
                    if img is not None:
                        logging.info("Image loaded successfully, computing HSV...")
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                        h, s, v = cv2.split(hsv)
                        mean_h = np.mean(h)
                        mean_s = np.mean(s)
                        mean_v = np.mean(v)
                        std_h = np.std(h)
                        std_s = np.std(s)
                        std_v = np.std(v)
                        stats_img = np.zeros((200, 400, 3), dtype=np.uint8)
                        cv2.putText(stats_img, f"Hue: mean={mean_h:.2f}, std={std_h:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        cv2.putText(stats_img, f"Sat: mean={mean_s:.2f}, std={std_s:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        cv2.putText(stats_img, f"Val: mean={mean_v:.2f}, std={std_v:.2f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        SHOW_DEBUG_WINDOWS = False  # Set to True to enable debug windows
                        if SHOW_DEBUG_WINDOWS:
                            logging.info("Displaying HSV statistics window...")
                            cv2.imshow("HSV Statistics", stats_img)
                            cv2.waitKey(2000)
                            cv2.destroyAllWindows()
                    else:
                        logging.warning("Failed to load image from %s", screenshot_path)
                else:
                    logging.warning("cv2 or numpy is not available; cannot compute HSV stats for %s", screenshot_path)
            except Exception:
                logging.exception("Failed to compute HSV stats while finalizing analysis for %s", screenshot_path)

        def __getattr__(self, name: str):
            """Proxy any unknown attribute access to the original analyzer instance.

            This covers methods like `capture_screenshot` that the original module
            provides but the wrapper doesn't explicitly implement.
            """
            return getattr(self._orig, name)
            return getattr(self._orig, name)

    ScreenAnalyzer = _WrappedScreenAnalyzer
else:
    # Could not import original analyzer; provide a minimal analyzer that uses vision_processor only
    class _FallbackScreenAnalyzer:
        def __init__(self, *args, **kwargs):
            self._cv = UniversalVisionProcessor() if UniversalVisionProcessor is not None else None

        def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
            import logging
            logging.info("Fallback analyze_screenshot start: %s", screenshot_path)

            result: Dict[str, Any] = {}
            try:
                if self._cv is None:
                    # Keep raising as before, but ensure HSV stats run in finally
                    raise RuntimeError("No vision processor available to analyze screenshots")
            finally:
                # Compute and display HSV statistics regardless of earlier errors
                try:
                    self._compute_and_display_hsv_stats(screenshot_path)
                except Exception:
                    logging.exception("Failed to compute HSV stats while finalizing analysis for %s", screenshot_path)

            return result
        def _compute_and_display_hsv_stats(self, screenshot_path: str):
            import logging
            try:
                logging.info("Computing HSV stats for %s", screenshot_path)
                if cv2 is not None and np is not None:
                    img = cv2.imread(screenshot_path)
                    if img is not None:
                        logging.info("Image loaded successfully, computing HSV...")
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                        h, s, v = cv2.split(hsv)
                        mean_h = np.mean(h)
                        mean_s = np.mean(s)
                        mean_v = np.mean(v)
                        std_h = np.std(h)
                        std_s = np.std(s)
                        std_v = np.std(v)
                        stats_img = np.zeros((200, 400, 3), dtype=np.uint8)
                        cv2.putText(stats_img, f"Hue: mean={mean_h:.2f}, std={std_h:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        cv2.putText(stats_img, f"Sat: mean={mean_s:.2f}, std={std_s:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        cv2.putText(stats_img, f"Val: mean={mean_v:.2f}, std={std_v:.2f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        SHOW_DEBUG_WINDOWS = False  # Set to True to enable debug windows
                        if SHOW_DEBUG_WINDOWS:
                            logging.info("Displaying HSV statistics window...")
                            cv2.imshow("HSV Statistics", stats_img)
                            cv2.waitKey(2000)
                            cv2.destroyAllWindows()
                    else:
                        logging.warning("Failed to load image from %s", screenshot_path)
                else:
                    logging.warning("cv2 or numpy is not available; cannot compute HSV stats for %s", screenshot_path)
            except Exception:
                logging.exception("Failed to compute HSV stats while finalizing analysis for %s", screenshot_path)

        def analyze_screen(self, screenshot_path: str) -> Dict[str, Any]:
            """Alias for analyze_screenshot for compatibility."""
            pyautogui = _try_import("pyautogui")
            """Capture a screenshot to the screenshots/ folder and return its path.

            Uses pyautogui if available, otherwise raises RuntimeError.
            """
            # Import pyautogui dynamically so static analyzers don't flag
            # missing optional packages in developer environments.
            try:
                pyautogui = importlib.import_module("pyautogui")
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
