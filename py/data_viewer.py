#!/usr/bin/env python3
"""
Data Viewer Application
Web-based application for viewing aggregated analysis cycle data in real-time.
Provides filtering, search, and detailed views of screenshots, reports, and AI responses.
"""
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import webbrowser
import sys
import os

from data_container import DataContainer, AnalysisCycle

logger = logging.getLogger(__name__)

class DataViewer:
    """Web-based data viewer for analysis cycles."""

    def __init__(self, data_container: DataContainer):
        """Initialize the data viewer."""
        self.data_container = data_container
        self.current_cycles: List[AnalysisCycle] = []

        # Register as a listener for real-time updates
        self.data_container.add_listener(self._on_data_update)

        logger.info("Data Viewer initialized")

    def launch(self):
        """Launch the web-based viewer."""
        try:
            self._launch_web()
        except Exception as e:
            logger.error(f"Web viewer failed: {e}")
            self._launch_cli()

    def _launch_web(self):
        """Launch the Flask web application."""
        try:
            from flask import Flask, render_template_string, request, jsonify, send_from_directory

            app = Flask(__name__, static_folder=str(Path(__file__).parent))

            # HTML template for the main page
            HTML_TEMPLATE = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Analysis Cycle Data Viewer</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: #f5f5f5;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }
                    .header {
                        background: #2c3e50;
                        color: white;
                        padding: 20px;
                        text-align: center;
                    }
                    .stats {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        padding: 20px;
                        background: #f8f9fa;
                        border-bottom: 1px solid #dee2e6;
                    }
                    .stat-card {
                        background: white;
                        padding: 15px;
                        border-radius: 6px;
                        text-align: center;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }
                    .stat-value {
                        font-size: 2em;
                        font-weight: bold;
                        color: #2c3e50;
                    }
                    .stat-label {
                        color: #6c757d;
                        margin-top: 5px;
                    }
                    .controls {
                        padding: 20px;
                        border-bottom: 1px solid #dee2e6;
                        background: #f8f9fa;
                    }
                    .search-group {
                        display: flex;
                        gap: 10px;
                        margin-bottom: 10px;
                        flex-wrap: wrap;
                    }
                    .search-group input, .search-group select {
                        padding: 8px 12px;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        font-size: 14px;
                    }
                    .search-group input {
                        flex: 1;
                        min-width: 200px;
                    }
                    .cycle-list {
                        max-height: 600px;
                        overflow-y: auto;
                    }
                    .cycle-item {
                        border: 1px solid #dee2e6;
                        margin: 10px;
                        border-radius: 6px;
                        overflow: hidden;
                        transition: box-shadow 0.2s;
                    }
                    .cycle-item:hover {
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    .cycle-header {
                        background: #f8f9fa;
                        padding: 15px;
                        cursor: pointer;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }
                    .cycle-title {
                        font-weight: 600;
                        color: #2c3e50;
                    }
                    .cycle-status {
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: 500;
                    }
                    .status-success { background: #d4edda; color: #155724; }
                    .status-error { background: #f8d7da; color: #721c24; }
                    .status-partial { background: #fff3cd; color: #856404; }
                    .cycle-details {
                        display: none;
                        padding: 15px;
                        border-top: 1px solid #dee2e6;
                        background: white;
                    }
                    .detail-section {
                        margin-bottom: 15px;
                    }
                    .detail-label {
                        font-weight: 600;
                        color: #495057;
                        margin-bottom: 5px;
                    }
                    .detail-content {
                        background: #f8f9fa;
                        padding: 10px;
                        border-radius: 4px;
                        font-family: 'Courier New', monospace;
                        white-space: pre-wrap;
                        word-break: break-word;
                        max-height: 300px;
                        overflow-y: auto;
                    }
                    .action-links {
                        margin-top: 10px;
                    }
                    .action-links a {
                        color: #007bff;
                        text-decoration: none;
                        margin-right: 15px;
                    }
                    .action-links a:hover {
                        text-decoration: underline;
                    }
                    .no-data {
                        text-align: center;
                        padding: 40px;
                        color: #6c757d;
                    }
                    .refresh-btn {
                        background: #007bff;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 14px;
                    }
                    .refresh-btn:hover {
                        background: #0056b3;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Analysis Cycle Data Viewer</h1>
                        <p>Real-time view of screen analysis cycles</p>
                    </div>

                    <div class="stats" id="stats">
                        <div class="stat-card">
                            <div class="stat-value" id="total-cycles">-</div>
                            <div class="stat-label">Total Cycles</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="error-rate">-%</div>
                            <div class="stat-label">Error Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="response-rate">-%</div>
                            <div class="stat-label">Response Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="avg-time">-.--s</div>
                            <div class="stat-label">Avg Processing Time</div>
                        </div>
                    </div>

                    <div class="controls">
                        <div class="search-group">
                            <input type="text" id="search" placeholder="Search in AI responses or errors...">
                            <select id="filter">
                                <option value="all">All Cycles</option>
                                <option value="with_errors">With Errors</option>
                                <option value="with_responses">With Responses</option>
                                <option value="successful">Successful</option>
                            </select>
                            <button class="refresh-btn" onclick="refreshData()">Refresh</button>
                        </div>
                        <div id="cycle-count">Loading cycles...</div>
                    </div>

                    <div class="cycle-list" id="cycle-list">
                        <div class="no-data">Loading cycles...</div>
                    </div>
                </div>

                <script>
                    let allCycles = [];
                    let filteredCycles = [];

                    async function refreshData() {
                        try {
                            // Fetch cycles
                            const cyclesResponse = await fetch('/api/cycles');
                            const cyclesData = await cyclesResponse.json();
                            allCycles = cyclesData.cycles || [];

                            // Fetch stats
                            const statsResponse = await fetch('/api/stats');
                            const statsData = await statsResponse.json();

                            updateStats(statsData);
                            applyFilters();
                        } catch (error) {
                            console.error('Error refreshing data:', error);
                            document.getElementById('cycle-list').innerHTML =
                                '<div class="no-data">Error loading data. Check console for details.</div>';
                        }
                    }

                    function updateStats(stats) {
                        document.getElementById('total-cycles').textContent = stats.total_cycles || 0;
                        document.getElementById('error-rate').textContent =
                            stats.error_rate ? (stats.error_rate * 100).toFixed(1) + '%' : '0%';
                        document.getElementById('response-rate').textContent =
                            stats.response_rate ? (stats.response_rate * 100).toFixed(1) + '%' : '0%';
                        document.getElementById('avg-time').textContent =
                            stats.average_processing_time ? stats.average_processing_time.toFixed(2) + 's' : 'N/A';
                    }

                    function applyFilters() {
                        const searchTerm = document.getElementById('search').value.toLowerCase();
                        const filterValue = document.getElementById('filter').value;

                        filteredCycles = allCycles.filter(cycle => {
                            // Apply filter
                            if (filterValue === 'with_errors' && !cycle.error_message) return false;
                            if (filterValue === 'with_responses' && !cycle.chatgpt_response) return false;
                            if (filterValue === 'successful' && (cycle.error_message || !cycle.chatgpt_response)) return false;

                            // Apply search
                            if (searchTerm) {
                                const searchText = (cycle.chatgpt_response || '') + (cycle.error_message || '');
                                if (!searchText.toLowerCase().includes(searchTerm)) return false;
                            }

                            return true;
                        });

                        updateCycleList();
                    }

                    function updateCycleList() {
                        const container = document.getElementById('cycle-list');
                        const count = document.getElementById('cycle-count');

                        count.textContent = `Showing ${filteredCycles.length} of ${allCycles.length} cycles`;

                        if (filteredCycles.length === 0) {
                            container.innerHTML = '<div class="no-data">No cycles match the current filters.</div>';
                            return;
                        }

                        container.innerHTML = '';

                        filteredCycles.forEach(cycle => {
                            const status = cycle.error_message ? 'error' :
                                         (cycle.chatgpt_response ? 'success' : 'partial');
                            const statusText = cycle.error_message ? 'Error' :
                                             (cycle.chatgpt_response ? 'Success' : 'Partial');

                            const cycleDiv = document.createElement('div');
                            cycleDiv.className = 'cycle-item';

                            cycleDiv.innerHTML = `
                                <div class="cycle-header" onclick="toggleDetails(${cycle.cycle_id})">
                                    <div class="cycle-title">Cycle ${cycle.cycle_id} - ${cycle.timestamp}</div>
                                    <div class="cycle-status status-${status}">${statusText}</div>
                                </div>
                                <div class="cycle-details" id="details-${cycle.cycle_id}">
                                    <div class="detail-section">
                                        <div class="detail-label">Processing Time</div>
                                        <div class="detail-content">${cycle.processing_time ? cycle.processing_time.toFixed(2) + 's' : 'N/A'}</div>
                                    </div>
                                    ${cycle.error_message ? `
                                    <div class="detail-section">
                                        <div class="detail-label">Error</div>
                                        <div class="detail-content">${cycle.error_message}</div>
                                    </div>
                                    ` : ''}
                                    ${cycle.chatgpt_response ? `
                                    <div class="detail-section">
                                        <div class="detail-label">AI Response</div>
                                        <div class="detail-content">${cycle.chatgpt_response}</div>
                                    </div>
                                    ` : ''}
                                    <div class="action-links">
                                        ${cycle.screenshot_path ? `<a href="/api/screenshot/${cycle.cycle_id}" target="_blank">View Screenshot</a>` : ''}
                                        ${cycle.report_path ? `<a href="/api/report/${cycle.cycle_id}" target="_blank">View Report</a>` : ''}
                                        ${cycle.chatgpt_response ? `<a href="/api/ai_overview/${cycle.cycle_id}" target="_blank">View AI Overview</a>` : ''}
                                    </div>
                                </div>
                            `;

                            container.appendChild(cycleDiv);
                        });
                    }

                    function toggleDetails(cycleId) {
                        const details = document.getElementById(`details-${cycleId}`);
                        const isVisible = details.style.display !== 'none';
                        details.style.display = isVisible ? 'none' : 'block';
                    }

                    // Event listeners
                    document.getElementById('search').addEventListener('input', applyFilters);
                    document.getElementById('filter').addEventListener('change', applyFilters);

                    // Initial load
                    refreshData();

                    // Auto-refresh every 30 seconds
                    setInterval(refreshData, 30000);
                </script>
            </body>
            </html>
            """

            @app.route('/')
            def index():
                return render_template_string(HTML_TEMPLATE)

            @app.route('/api/cycles')
            def get_cycles():
                cycles = self.data_container.get_all_cycles()
                return jsonify({'cycles': [cycle.__dict__ for cycle in cycles]})

            @app.route('/api/stats')
            def get_stats():
                return jsonify(self.data_container.get_statistics_summary())

            @app.route('/api/screenshot/<int:cycle_id>')
            def get_screenshot(cycle_id):
                cycle = self.data_container.get_cycle(cycle_id)
                if cycle and cycle.screenshot_path and Path(cycle.screenshot_path).exists():
                    directory = str(Path(cycle.screenshot_path).parent)
                    filename = Path(cycle.screenshot_path).name
                    return send_from_directory(directory, filename)
                return jsonify({'error': 'Screenshot not found'}), 404

            @app.route('/api/report/<int:cycle_id>')
            def get_report(cycle_id):
                cycle = self.data_container.get_cycle(cycle_id)
                if cycle and cycle.report_path and Path(cycle.report_path).exists():
                    directory = str(Path(cycle.report_path).parent)
                    filename = Path(cycle.report_path).name
                    return send_from_directory(directory, filename)
                return jsonify({'error': 'Report not found'}), 404

            @app.route('/api/ai_overview/<int:cycle_id>')
            def get_ai_overview(cycle_id):
                cycle = self.data_container.get_cycle(cycle_id)
                if not cycle:
                    return f"<h1>Error</h1><p>Cycle {cycle_id} not found.</p>", 404

                if not cycle.chatgpt_response:
                    return f"<h1>No AI Overview Available</h1><p>Cycle {cycle_id} does not have an AI response.</p>", 404

                # Format processing time
                processing_time_display = f"{cycle.processing_time:.2f}s" if cycle.processing_time else "N/A"

                # Create a simple HTML page with the AI overview
                html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>AI Overview - Cycle {cycle_id}</title>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            margin: 20px;
                            background: #f5f5f5;
                        }}
                        .container {{
                            max-width: 800px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            padding: 20px;
                        }}
                        .header {{
                            border-bottom: 1px solid #dee2e6;
                            padding-bottom: 15px;
                            margin-bottom: 20px;
                        }}
                        .title {{
                            color: #2c3e50;
                            margin: 0;
                        }}
                        .meta {{
                            color: #6c757d;
                            font-size: 14px;
                            margin-top: 5px;
                        }}
                        .content {{
                            line-height: 1.6;
                            white-space: pre-wrap;
                            background: #f8f9fa;
                            padding: 15px;
                            border-radius: 6px;
                            border-left: 4px solid #007bff;
                        }}
                        .back-link {{
                            display: inline-block;
                            margin-top: 20px;
                            color: #007bff;
                            text-decoration: none;
                        }}
                        .back-link:hover {{
                            text-decoration: underline;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1 class="title">AI Overview - Cycle {cycle_id}</h1>
                            <div class="meta">
                                Timestamp: {cycle.timestamp}<br>
                                Processing Time: {processing_time_display}
                            </div>
                        </div>
                        <div class="content">
                            {cycle.chatgpt_response}
                        </div>
                        <a href="javascript:history.back()" class="back-link">← Back to Viewer</a>
                    </div>
                </body>
                </html>
                """
                return html_content

            # Start the server
            port = 5000
            url = f"http://localhost:{port}"

            # Open browser after a short delay to let server start
            def open_browser():
                time.sleep(1)
                webbrowser.open(url)

            threading.Thread(target=open_browser, daemon=True).start()

            logger.info(f"Web viewer starting at {url}")
            print(f"\n🚀 Data Viewer launched at: {url}")
            print("📊 View real-time analysis cycle data")
            print("🔄 Auto-refreshes every 30 seconds")
            print("Press Ctrl+C to stop the viewer\n")

            app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

        except ImportError as e:
            raise Exception(f"Flask not available: {e}. Install with: pip install flask")

    def _launch_cli(self):
        """Launch a simple command-line interface as fallback."""
        print("\n=== Analysis Cycle Data Viewer (CLI Fallback) ===")
        print("Web viewer failed. Using basic command-line interface.\n")

        while True:
            print("\nCommands:")
            print("  list - List recent cycles")
            print("  stats - Show statistics")
            print("  view <id> - View cycle details")
            print("  search <term> - Search cycles")
            print("  export - Export data to JSON")
            print("  quit - Exit viewer")

            try:
                cmd = input("\n> ").strip()
                if not cmd:
                    continue

                if cmd == 'quit':
                    break
                elif cmd == 'list':
                    self._cli_list_cycles()
                elif cmd == 'stats':
                    self._cli_show_stats()
                elif cmd.startswith('view '):
                    try:
                        cycle_id = int(cmd.split()[1])
                        self._cli_view_cycle(cycle_id)
                    except (ValueError, IndexError):
                        print("Usage: view <cycle_id>")
                elif cmd.startswith('search '):
                    term = cmd[7:]  # Remove 'search '
                    if term:
                        self._cli_search(term)
                    else:
                        print("Usage: search <term>")
                elif cmd == 'export':
                    self._cli_export()
                else:
                    print("Unknown command. Type 'quit' to exit.")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _cli_list_cycles(self):
        """CLI command to list recent cycles."""
        cycles = self.data_container.get_all_cycles()
        if not cycles:
            print("No cycles found.")
            return

        print(f"\nRecent cycles (last {min(10, len(cycles))}):")
        for cycle in cycles[-10:]:
            status = "❌ Error" if cycle.error_message else ("✅ Success" if cycle.chatgpt_response else "⚠️  Partial")
            print(f"  {cycle.cycle_id}: {cycle.timestamp} - {status}")

    def _cli_show_stats(self):
        """CLI command to show statistics."""
        stats = self.data_container.get_statistics_summary()
        print("\n📊 Statistics:")
        print(f"  Total Cycles: {stats.get('total_cycles', 0)}")
        print(f"  Error Rate: {(stats.get('error_rate', 0) * 100):.1f}%")
        print(f"  Response Rate: {(stats.get('response_rate', 0) * 100):.1f}%")
        if stats.get('average_processing_time'):
            print(f"  Avg Processing Time: {stats['average_processing_time']:.2f}s")

    def _cli_view_cycle(self, cycle_id: int):
        """CLI command to view cycle details."""
        cycle = self.data_container.get_cycle(cycle_id)
        if not cycle:
            print(f"Cycle {cycle_id} not found.")
            return

        print(f"\n🔍 Cycle {cycle_id} Details:")
        print(f"  Timestamp: {cycle.timestamp}")
        print(f"  Processing Time: {cycle.processing_time:.2f}s" if cycle.processing_time else "  Processing Time: N/A")
        print(f"  Screenshot: {cycle.screenshot_path or 'None'}")
        print(f"  Report: {cycle.report_path or 'None'}")

        if cycle.error_message:
            print(f"  ❌ Error: {cycle.error_message}")

        if cycle.chatgpt_response:
            print(f"\n🤖 AI Response:")
            print(f"  {cycle.chatgpt_response}")

    def _cli_search(self, term: str):
        """CLI command to search cycles."""
        results = self.data_container.search_cycles(term)
        if not results:
            print(f"No cycles found containing '{term}'.")
            return

        print(f"\n🔎 Search results for '{term}': {len(results)} matches")
        for cycle in results[:10]:  # Limit to first 10 results
            status = "Error" if cycle.error_message else ("Success" if cycle.chatgpt_response else "Partial")
            print(f"  Cycle {cycle.cycle_id}: {cycle.timestamp} - {status}")

        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more results")

    def _cli_export(self):
        """CLI command to export data."""
        filename = input("Export filename (default: data_export.json): ").strip()
        if not filename:
            filename = "data_export.json"

        try:
            self.data_container.export_to_json(filename)
            print(f"✅ Data exported to {filename}")
        except Exception as e:
            print(f"❌ Export failed: {e}")

    def _on_data_update(self, event_type, data):
        """Handle data container updates (for future real-time features)."""
        pass


def main():
    """Launch the data viewer application."""
    # Initialize data container
    container = DataContainer()

    # Create and launch the viewer
    viewer = DataViewer(container)
    viewer.launch()


if __name__ == "__main__":
    main()