import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from base64 import b64decode
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "modbapi_imagegen.py")
SPEC = importlib.util.spec_from_file_location("modbapi_imagegen", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class Handler(BaseHTTPRequestHandler):
    polls = 0
    received = None
    result_url = None
    image_user_agent = None
    image = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+AvzEGwAAAABJRU5ErkJggg==")
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
        if self.path == "/result.png":
            Handler.image_user_agent = self.headers.get("User-Agent")
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(Handler.image)))
            self.end_headers()
            self.wfile.write(Handler.image)
            return
        Handler.polls += 1
        self._send({"id": "task_test", "status": "completed", "detail": {"data": [{"download_url": Handler.result_url}]}})

class ModbapiImagegenTests(unittest.TestCase):
    def test_async_generation_prints_renderable_image(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        Handler.polls = 0
        Handler.result_url = f"http://127.0.0.1:{server.server_port}/result.png"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "result.png")
            try:
                env = dict(os.environ, MODBAPI_API_KEY="test-key")
                result = subprocess.run([
                    sys.executable, SCRIPT, "--prompt", "test image",
                    "--base-url", f"http://127.0.0.1:{server.server_port}",
                    "--interval", "0.01", "--output", output, "--size", "16:9",
                ], capture_output=True, text=True, env=env, check=False)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            self.assertEqual(Path(output).read_bytes(), Handler.image)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Handler.received["response_format"], "url")
        self.assertEqual(Handler.received["size"], "1024x576")
        self.assertIn(f"IMAGE_URL={Handler.result_url}", result.stdout)
        self.assertIn(f"IMAGE_PATH={output}", result.stdout)
        self.assertIn(f"![Generated image]({output})", result.stdout)
        self.assertEqual(Handler.image_user_agent, "modbapi-imagegen/1.0")
        self.assertGreaterEqual(Handler.polls, 1)

    def test_url_only_preserves_remote_rendering(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        Handler.result_url = "https://cdn.example.test/result.png"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = dict(os.environ, MODBAPI_API_KEY="test-key")
            result = subprocess.run([
                sys.executable, SCRIPT, "--prompt", "test image",
                "--base-url", f"http://127.0.0.1:{server.server_port}",
                "--interval", "0.01", "--url-only",
            ], capture_output=True, text=True, env=env, check=False)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("IMAGE_PATH=", result.stdout)
        self.assertIn("![Generated image](https://cdn.example.test/result.png)", result.stdout)

    def test_missing_key_is_actionable(self):
        env = dict(os.environ, MODBAPI_API_KEY_FILE="/path/that/does/not/exist")
        env.pop("MODBAPI_API_KEY", None)
        result = subprocess.run([sys.executable, SCRIPT, "--prompt", "test"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("MODBAPI_API_KEY is not set", result.stderr)

    def test_size_presets_and_api_supported_exact_sizes(self):
        expected = {
            "1:1": "1024x1024",
            "16:9": "1024x576",
            "9:16": "576x1024",
            "4:3": "1024x768",
            "3:4": "768x1024",
        }
        for ratio, size in expected.items():
            with self.subTest(ratio=ratio):
                self.assertEqual(MODULE.normalize_size(ratio), size)
                self.assertEqual(MODULE.normalize_size(size), size)
        self.assertEqual(MODULE.normalize_size("1672x940"), "1672x940")
        self.assertEqual(MODULE.normalize_size("2048x1024"), "2048x1024")

    def test_malformed_size_is_rejected(self):
        for size in ("0x1024", "1024x0", "wide", "16:10"):
            with self.subTest(size=size), self.assertRaises(argparse.ArgumentTypeError):
                MODULE.normalize_size(size)

if __name__ == "__main__":
    unittest.main()
