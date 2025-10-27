import threading
import http.server
import socketserver
import json
import time
from app.notifiers.webhook_dispatcher import WebhookDispatcher, verify_signature

PORT = 9109
SECRET = "test-secret"
RECEIVED = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        ts = self.headers.get("X-Sniper-Timestamp")
        sig = self.headers.get("X-Sniper-Signature")
        ok = verify_signature(SECRET, ts, body, sig or "")
        RECEIVED["ok"] = ok
        RECEIVED["body"] = json.loads(body.decode("utf-8"))
        self.send_response(200 if ok else 400)
        self.end_headers()

    def log_message(self, *args, **kwargs):  # silence
        pass


def run_server():
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.timeout = 5
        httpd.handle_request()
        httpd.server_close()


def test_dispatch_sends_and_verifies_signature():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(0.05)

    disp = WebhookDispatcher(
        url=f"http://127.0.0.1:{PORT}/hook", secret=SECRET, cfg={"min_score": 0.1}
    )
    events = [{"id": "1", "flipScore": 0.95, "title": "Test Listing"}]
    res = disp.dispatch(events)
    assert res["sent"] == 1
    assert RECEIVED.get("ok") is True
    assert RECEIVED["body"]["title"] == "Test Listing"
