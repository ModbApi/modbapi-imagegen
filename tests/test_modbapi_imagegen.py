import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "modbapi_imagegen.py")

class Handler(BaseHTTPRequestHandler):
    polls = 0
    received = None
    def log_message(self, *_):
        pass
    def _send(self, payload, code=200):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        Handler.received = json.loads(self.rfile.read(length))
        self._send({"id": "task_test", "task_id": "task_test", "status": "queued"}, 202)
    def do_GET(self):
        Handler.polls += 1
        self._send({"id": "task_test", "status": "completed", "detail": {"data": [{"download_url": "https://cdn.example.test/result.png"}]}})

class ModbapiImagegenTests(unittest.TestCase):
    def test_async_generation_prints_renderable_image(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = dict(os.environ, MODBAPI_API_KEY="test-key")
            result = subprocess.run([
                sys.executable, SCRIPT, "--prompt", "test image",
                "--base-url", f"http://127.0.0.1:{server.server_port}",
                "--interval", "0.01",
            ], capture_output=True, text=True, env=env, check=False)
        finally:
            server.shutdown()
            thread.join(timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Handler.received["response_format"], "url")
        self.assertIn("IMAGE_URL=https://cdn.example.test/result.png", result.stdout)
        self.assertIn("![Generated image](https://cdn.example.test/result.png)", result.stdout)
        self.assertGreaterEqual(Handler.polls, 1)

    def test_missing_key_is_actionable(self):
        env = dict(os.environ)
        env.pop("MODBAPI_API_KEY", None)
        result = subprocess.run([sys.executable, SCRIPT, "--prompt", "test"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("MODBAPI_API_KEY is not set", result.stderr)

if __name__ == "__main__":
    unittest.main()
