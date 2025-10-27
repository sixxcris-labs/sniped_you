import http.server
import hmac
import hashlib
import os


class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        ts = self.headers.get("X-Sniper-Timestamp", "")
        sig = self.headers.get("X-Sniper-Signature", "")
        secret = os.environ.get("SNIPER_WEBHOOK_SECRET", "test-secret")
        calc = (
            "sha256="
            + hmac.new(
                secret.encode(), (ts + "." + body.decode()).encode(), hashlib.sha256
            ).hexdigest()
        )
        ok = sig == calc
        self.send_response(200 if ok else 401)
        self.end_headers()
        print({"ok": ok, "sig": sig, "calc": calc, "len": len(body)})


http.server.HTTPServer(("0.0.0.0", 8000), H).serve_forever()
