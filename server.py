import http.server
import socketserver
import json
import time
import threading
from urllib.parse import urlparse, parse_qs

# ── Presence tracking ──────────────────────────────────────────
SESSIONS = {}          # {session_id: last_seen_timestamp}
SESSIONS_LOCK = threading.Lock()
SESSION_TTL = 35       # seconds — expire a session this long after last heartbeat

def prune_sessions():
    now = time.time()
    with SESSIONS_LOCK:
        expired = [k for k, v in SESSIONS.items() if now - v > SESSION_TTL]
        for k in expired:
            del SESSIONS[k]

def pruner_loop():
    while True:
        time.sleep(10)
        prune_sessions()

threading.Thread(target=pruner_loop, daemon=True).start()

# ── Request handler ────────────────────────────────────────────
class Handler(http.server.SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # POST-style heartbeat via GET (simpler for JS fetch)
        if parsed.path == '/api/heartbeat':
            qs = parse_qs(parsed.query)
            sid = qs.get('id', [None])[0]
            if sid:
                with SESSIONS_LOCK:
                    SESSIONS[sid] = time.time()
            self._json({'ok': True})
            return

        if parsed.path == '/api/online':
            prune_sessions()
            with SESSIONS_LOCK:
                count = len(SESSIONS)
            self._json({'online': count})
            return

        super().do_GET()

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Suppress /api noise from logs
        if '/api/' not in args[0]:
            print(fmt % args)

socketserver.TCPServer.allow_reuse_address = True
PORT = 5000
with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f'Serving on port {PORT}')
    httpd.serve_forever()
