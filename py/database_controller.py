#!/usr/bin/env python3
"""
Database Controller GUI for managing screen analysis cycles.
Provides a Tkinter interface to view, query, and manage stored cycles.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import subprocess
import sys
from pathlib import Path
from database import CycleDatabase

class DatabaseController:
    """Tkinter GUI for database management."""

    def __init__(self, root):
        self.root = root
        self.root.title("Screen Analysis Cycles Database")
        self.root.geometry("800x600")

        self.db = CycleDatabase()

        # Create widgets
        self.create_widgets()
        self.load_cycles()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Listbox for cycles
        list_frame = ttk.LabelFrame(main_frame, text="Cycles")
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.cycle_listbox = tk.Listbox(list_frame, width=40, height=20)
        self.cycle_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.cycle_listbox.bind('<<ListboxSelect>>', self.on_cycle_select)

        # Buttons
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Refresh", command=self.load_cycles).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.delete_cycle).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="View Report", command=self.view_report).pack(side=tk.LEFT, padx=2)

        # Details frame
        details_frame = ttk.LabelFrame(main_frame, text="Cycle Details")
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.details_text = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, width=50, height=25)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_cycles(self):
        """Load and display all cycles."""
        self.cycle_listbox.delete(0, tk.END)
        self.cycles = self.db.get_all_cycles()
        for cycle in self.cycles:
            display_text = f"ID {cycle['id']}: {cycle['timestamp']}"
            self.cycle_listbox.insert(tk.END, display_text)

    def on_cycle_select(self, event):
        """Handle cycle selection."""
        selection = self.cycle_listbox.curselection()
        if selection:
            index = selection[0]
            cycle = self.cycles[index]
            self.display_cycle_details(cycle)

    def display_cycle_details(self, cycle):
        """Display detailed information about a cycle."""
        self.details_text.delete(1.0, tk.END)

        details = f"Cycle ID: {cycle['id']}\n"
        details += f"Timestamp: {cycle['timestamp']}\n"
        details += f"Screenshot: {cycle['screenshot_path'] or 'N/A'}\n"
        details += f"Report: {cycle['report_path'] or 'N/A'}\n\n"

        if cycle['chatgpt_response']:
            details += "ChatGPT Response:\n" + cycle['chatgpt_response'] + "\n\n"
        else:
            details += "ChatGPT Response: N/A\n\n"

        if cycle['statistics']:
            details += "Statistics:\n" + json.dumps(cycle['statistics'], indent=2)
        else:
            details += "Statistics: N/A"

        self.details_text.insert(tk.END, details)

    def delete_cycle(self):
        """Delete the selected cycle."""
        selection = self.cycle_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a cycle to delete.")
            return

        index = selection[0]
        cycle = self.cycles[index]

        if messagebox.askyesno("Confirm Delete", f"Delete cycle ID {cycle['id']}?"):
            if self.db.delete_cycle(cycle['id']):
                messagebox.showinfo("Success", "Cycle deleted.")
                self.load_cycles()
                self.details_text.delete(1.0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to delete cycle.")

    def view_report(self):
        """Open the report file for the selected cycle."""
        selection = self.cycle_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a cycle to view report.")
            return

        index = selection[0]
        cycle = self.cycles[index]
        report_path = cycle['report_path']

        if not report_path:
            messagebox.showwarning("No Report", "No report file available for this cycle.")
            return

        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", report_path])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["start", report_path], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", report_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open report: {e}")

def main():
    root = tk.Tk()
    app = DatabaseController(root)
    root.mainloop()

if __name__ == "__main__":
    main()