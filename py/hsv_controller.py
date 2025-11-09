"""
Small controller window to display live HSV (Hue/Saturation/Value) statistics
for the entire screen. Uses Pillow to capture the screen, OpenCV + NumPy to
compute HSV statistics, and Tkinter for a simple UI.

Run with:
    python py/hsv_controller.py

Notes:
- On macOS you must grant screen-recording permission for the terminal/Python
  process in System Settings -> Privacy & Security -> Screen Recording.
- Requires: Pillow, opencv-python, numpy
"""
from __future__ import annotations
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Tuple

from PIL import ImageGrab, Image
import numpy as np
import cv2

logging.basicConfig(level=logging.INFO)

UPDATE_INTERVAL_S = 1.0  # default live update interval (seconds)


def compute_hsv_stats_from_image(img: Image.Image) -> Tuple[float, float, float, float, float, float]:
    """Return mean_h, mean_s, mean_v, std_h, std_s, std_v for a PIL image."""
    # Convert PIL image (RGB) to BGR numpy array for OpenCV
    arr = np.asarray(img.convert("RGB"))
    # convert RGB -> BGR
    bgr = arr[:, :, ::-1].copy()
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    mean_h = float(np.mean(h))
    mean_s = float(np.mean(s))
    mean_v = float(np.mean(v))
    std_h = float(np.std(h))
    std_s = float(np.std(s))
    std_v = float(np.std(v))
    return mean_h, mean_s, mean_v, std_h, std_s, std_v


class HSVController(tk.Tk):
    def __init__(self, update_interval: float = UPDATE_INTERVAL_S):
        super().__init__()
        self.title("HSV Controller")
        self.geometry("360x220")
        self.resizable(False, False)

        self.update_interval = update_interval
        self._running = False
        self._worker_thread = None
        self._stop_event = threading.Event()

        # UI
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        self.labels = {}
        row = 0
        for name in ("Hue", "Saturation", "Value"):
            ttk.Label(frm, text=f"{name}:", width=12).grid(column=0, row=row, sticky=tk.W)
            lbl_mean = ttk.Label(frm, text="mean=—", width=22)
            lbl_mean.grid(column=1, row=row, sticky=tk.W)
            row += 1
            ttk.Label(frm, text="").grid(column=0, row=row)  # spacer
            row += 1
        # second column will show std values inline (we update the same labels)

        # control buttons
        btn_row = row
        self.toggle_btn = ttk.Button(frm, text="Start Live", command=self.toggle_live)
        self.toggle_btn.grid(column=0, row=btn_row, columnspan=1, sticky=tk.W)

        self.snapshot_btn = ttk.Button(frm, text="One-shot", command=self.one_shot)
        self.snapshot_btn.grid(column=1, row=btn_row, sticky=tk.E)

        self.close_btn = ttk.Button(frm, text="Close", command=self.close)
        self.close_btn.grid(column=0, row=btn_row + 1, columnspan=2, pady=(8, 0))

        # status bar
        self.status = tk.StringVar(value="Idle")
        ttk.Label(self, textvariable=self.status, relief=tk.SUNKEN).pack(fill=tk.X, side=tk.BOTTOM)

        # create labels references for update
        self.hue_label = lbl_mean  # placeholder; we'll update by grabbing grid
        # Instead, store the three label widgets manually
        # Recreate proper labels layout for clarity
        for child in frm.winfo_children():
            child.destroy()
        row = 0
        self.hue_lbl = ttk.Label(frm, text="Hue: mean=—, std=—")
        self.hue_lbl.grid(column=0, row=row, columnspan=2, sticky=tk.W)
        row += 1
        self.sat_lbl = ttk.Label(frm, text="Sat: mean=—, std=—")
        self.sat_lbl.grid(column=0, row=row, columnspan=2, sticky=tk.W)
        row += 1
        self.val_lbl = ttk.Label(frm, text="Val: mean=—, std=—")
        self.val_lbl.grid(column=0, row=row, columnspan=2, sticky=tk.W)
        row += 1

        self.toggle_btn = ttk.Button(frm, text="Start Live", command=self.toggle_live)
        self.toggle_btn.grid(column=0, row=row, sticky=tk.W, pady=(12, 0))
        self.snapshot_btn = ttk.Button(frm, text="One-shot", command=self.one_shot)
        self.snapshot_btn.grid(column=1, row=row, sticky=tk.E, pady=(12, 0))
        row += 1
        self.close_btn = ttk.Button(frm, text="Close", command=self.close)
        self.close_btn.grid(column=0, row=row, columnspan=2, pady=(8, 0))

    def one_shot(self) -> None:
        """Capture one screenshot and update labels."""
        try:
            self.status.set("Capturing...")
            img = ImageGrab.grab()
            stats = compute_hsv_stats_from_image(img)
            self._update_labels(stats)
            self.status.set("Captured")
        except Exception as e:
            logging.exception("One-shot capture failed: %s", e)
            self.status.set("Error: see console")

    def toggle_live(self) -> None:
        if self._running:
            self.stop_live()
        else:
            self.start_live()

    def start_live(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self.toggle_btn.config(text="Stop Live")
        self.status.set("Live: running")
        self._worker_thread = threading.Thread(target=self._live_loop, daemon=True)
        self._worker_thread.start()

    def stop_live(self) -> None:
        if not self._running:
            return
        self._stop_event.set()
        self._worker_thread.join(timeout=2.0)
        self._running = False
        self.toggle_btn.config(text="Start Live")
        self.status.set("Idle")

    def _live_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                img = ImageGrab.grab()
                stats = compute_hsv_stats_from_image(img)
                # schedule UI update on main thread
                self.after(0, self._update_labels, stats)
                time.sleep(self.update_interval)
        except Exception:
            logging.exception("Live loop failed")
            self.after(0, lambda: self.status.set("Error in live loop"))

    def _update_labels(self, stats: Tuple[float, float, float, float, float, float]) -> None:
        mean_h, mean_s, mean_v, std_h, std_s, std_v = stats
        # Hue in OpenCV ranges 0-179; normalize for display optionally
        self.hue_lbl.config(text=f"Hue: mean={mean_h:.1f}, std={std_h:.1f}")
        self.sat_lbl.config(text=f"Sat: mean={mean_s:.1f}, std={std_s:.1f}")
        self.val_lbl.config(text=f"Val: mean={mean_v:.1f}, std={std_v:.1f}")

    def close(self) -> None:
        self.stop_live()
        self.destroy()


def main() -> None:
    app = HSVController(update_interval=1.0)
    app.mainloop()


if __name__ == "__main__":
    main()
