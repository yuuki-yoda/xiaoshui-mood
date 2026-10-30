#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小水的心情挂饰 —— 极简 HTTP 服务（stdlib，无依赖）。
监听 127.0.0.1:19005，由 nginx /mood/ 反代。
路由:
  GET /            挂饰页
  GET /api/state   心情 JSON
"""
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "mood-widget.html")
MOOD = os.path.join(HERE, "mood.py")
PORT = int(os.environ.get("MOOD_PORT", "19005"))


def read_state():
    out = subprocess.check_output([sys.executable, MOOD, "json"], timeout=10)
    return out


class H(BaseHTTPRequestHandler):
    server_version = "xiaoshui-mood/1.0"

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/api/state", "/api/state/"):
                self._send(200, read_state())
            elif path in ("/", "/index.html"):
                with open(HTML, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            elif path == "/health":
                self._send(200, b'{"ok":true}')
            else:
                self._send(404, b'{"error":"not found"}')
        except subprocess.TimeoutExpired:
            self._send(500, b'{"error":"timeout"}')
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", PORT), H)
    sys.stderr.write("mood server on 127.0.0.1:%d\n" % PORT)
    srv.serve_forever()
