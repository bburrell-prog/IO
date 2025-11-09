#!/usr/bin/env python3
"""
Lightweight HTTP-based database controller fallback.
Serves a simple HTML UI to list and view cycles from the SQLite DB.
No external dependencies.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import socket
from database import CycleDatabase


def find_free_port(start=8000, end=9000):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return 8000


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ('/', '/index'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            db = CycleDatabase()
            cycles = db.get_all_cycles()
            self.wfile.write(b"<html><head><meta charset='utf-8'><title>Cycles</title></head><body>")
            self.wfile.write(b"<h1>Saved Analysis Cycles</h1>")
            self.wfile.write(b"<p>Click an ID to view details.</p>")
            self.wfile.write(b"<ul>")
            for c in cycles:
                line = f"<li><a href='/cycle?id={c['id']}'>ID {c['id']}: {c['timestamp']}</a></li>"
                self.wfile.write(line.encode('utf-8'))
            self.wfile.write(b"</ul>")
            self.wfile.write(b"</body></html>")

        elif path == '/cycle':
            if 'id' not in qs:
                self.send_response(400)
                self.end_headers()
                return
            try:
                cycle_id = int(qs['id'][0])
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            db = CycleDatabase()
            cycle = db.get_cycle_by_id(cycle_id)
            if not cycle:
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<html><head><meta charset='utf-8'><title>Cycle</title></head><body>")
            self.wfile.write(f"<h1>Cycle ID {cycle['id']}</h1>".encode('utf-8'))
            self.wfile.write(f"<p><strong>Timestamp:</strong> {cycle['timestamp']}</p>".encode('utf-8'))
            self.wfile.write(f"<p><strong>Screenshot:</strong> {cycle['screenshot_path'] or 'N/A'}</p>".encode('utf-8'))
            self.wfile.write(f"<p><strong>Report:</strong> {cycle['report_path'] or 'N/A'}</p>".encode('utf-8'))
            self.wfile.write(b"<h2>ChatGPT Response</h2>")
            self.wfile.write(f"<pre>{(cycle['chatgpt_response'] or 'N/A')}</pre>".encode('utf-8'))
            self.wfile.write(b"<h2>Statistics</h2>")
            if cycle['statistics']:
                pretty = json.dumps(cycle['statistics'], indent=2)
                self.wfile.write(f"<pre>{pretty}</pre>".encode('utf-8'))
            else:
                self.wfile.write(b"<p>N/A</p>")
            self.wfile.write(b"</body></html>")

        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = find_free_port()
    addr = ('127.0.0.1', port)
    print(f"Starting web DB controller at http://{addr[0]}:{addr[1]}/")
    httpd = HTTPServer(addr, Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down web controller')
        httpd.server_close()


if __name__ == '__main__':
    main()
