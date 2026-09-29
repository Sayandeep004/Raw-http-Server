# raw-http-server

**Lightweight HTTP/1.1 server implemented from raw TCP sockets (educational).**

A minimal, single-file HTTP/1.1 server implemented using Python sockets (no frameworks).  
It parses HTTP request lines and headers, serves static files with correct MIME types and `Content-Length`, and exposes a simple monitoring endpoint `/api/status`. The server is multi-threaded (thread-per-connection) for simple concurrency and includes directory traversal protection.

> **Goal:** teach and demonstrate how HTTP works at Layer 7 while showing system-level networking (socket lifecycle, CRLF framing, Content-Length) and simple validation tooling.

---

## Features

- Plain Python sockets (no Flask / Django / external web frameworks)
- Manual HTTP/1.1 parsing (request-line, headers, CRLF framing)
- Static file serving with MIME type detection (`mimetypes`)
- `/api/status` endpoint returning runtime info (uptime, request count, thread count)
- Directory traversal protection (`os.path.commonpath`)
- Per-connection worker threads (simple concurrency)
- Small, demo-friendly footprint — easy to inspect & explain in interviews

---

## Quickstart

> Tested on Python 3.10+ (works on 3.8+). Use a virtual environment for local testing.

```bash
# (optional) create and activate a venv
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows PowerShell

# install dependencies (likely none; keep this for future libs)
pip install -r requirements.txt

# run the server on default port 8080
python server.py 8080
