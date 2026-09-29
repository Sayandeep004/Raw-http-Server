"""
Lightweight Multi-Threaded HTTP/1.1 Web Server from Scratch.

Built using raw TCP sockets without any external frameworks (no Flask, Django, etc.).

Key Networking Concepts Demonstrated:
1. Socket lifecycle: socket() -> setsockopt() -> bind() -> listen() -> accept() -> recv() -> sendall() -> close()
2. Layer 4 (TCP stream) vs Layer 7 (HTTP application protocol parsing)
3. HTTP protocol framing: Request line, Headers, Body, and CRLF (\\r\\n) delimiters
4. MIME types and HTTP status codes (200 OK, 404 Not Found, 400 Bad Request)
5. Multi-threaded concurrency for simultaneous client connections
"""

from datetime import datetime, timezone
import json
import mimetypes
import os
import socket
import sys
import threading
import time

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
SERVER_NAME = "PythonRawSocketServer/1.0"


class RawHTTPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.start_time = time.time()
        self.request_count = 0
        self.running = False
        self.server_sock = None

    def start(self):
        # 1. Create a TCP socket (AF_INET = IPv4, SOCK_STREAM = TCP)
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 2. Allow immediate socket reuse after server restart (avoids TIME_WAIT port lock)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 3. Bind the socket to IP address and port
        self.server_sock.bind((self.host, self.port))

        # 4. Put socket into listening mode with a connection backlog queue of 10
        self.server_sock.listen(10)
        self.running = True

        print("=" * 68)
        print(f" Raw TCP Socket HTTP Web Server Running!")
        print(f" Listening at : http://{self.host}:{self.port}/")
        print(f" Document Root: {PUBLIC_DIR}")
        print(f" Press Ctrl+C to terminate.")
        print("=" * 68)

        try:
            while self.running:
                # 5. accept() blocks until a new client completes the TCP 3-way handshake
                try:
                    client_sock, client_addr = self.server_sock.accept()
                except OSError:
                    break

                self.request_count += 1
                # 6. Spawn a worker thread to handle the client concurrently
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, client_addr),
                    daemon=True,
                )
                thread.start()

        except KeyboardInterrupt:
            print("\n[Server] Shutting down gracefully...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
        print("[Server] Stopped.")

    def _handle_client(self, client_sock: socket.socket, client_addr: tuple):
        """Processes an incoming HTTP connection from a client."""
        client_sock.settimeout(5.0)  # 5-second timeout for slow clients
        try:
            # Receive raw bytes sent by the client browser/tool
            raw_data = client_sock.recv(4096)
            if not raw_data:
                return

            request_text = raw_data.decode("utf-8", errors="ignore")
            lines = request_text.split("\r\n")

            # Validate HTTP request format
            if len(lines) == 0 or not lines[0]:
                return

            # Parse Request Line: e.g. "GET /index.html HTTP/1.1"
            parts = lines[0].split()
            if len(parts) < 3:
                self._send_response(client_sock, 400, "Bad Request", b"Bad Request", "text/plain")
                return

            method, raw_path, http_version = parts[0], parts[1], parts[2]
            clean_path = raw_path.split("?")[0]  # strip query string

            # Route 1: REST API Endpoint (/api/status)
            if clean_path == "/api/status":
                uptime = round(time.time() - self.start_time, 2)
                api_data = {
                    "status": "HEALTHY",
                    "server": SERVER_NAME,
                    "uptime_seconds": uptime,
                    "total_requests_served": self.request_count,
                    "active_threads": threading.active_count(),
                    "client_ip": client_addr[0],
                    "client_port": client_addr[1],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                body_bytes = json.dumps(api_data, indent=2).encode("utf-8")
                self._send_response(client_sock, 200, "OK", body_bytes, "application/json")
                self._log(client_addr, method, clean_path, 200)
                return

            # Route 2: Static Files
            if clean_path == "/":
                clean_path = "/index.html"

            # Security: Prevent Directory Traversal attack (e.g. /../../etc/passwd)
            safe_rel_path = os.path.normpath(clean_path.lstrip("/"))
            file_path = os.path.join(PUBLIC_DIR, safe_rel_path)

            if not os.path.commonpath([PUBLIC_DIR, os.path.abspath(file_path)]) == PUBLIC_DIR:
                self._send_response(client_sock, 403, "Forbidden", b"Forbidden", "text/plain")
                self._log(client_addr, method, clean_path, 403)
                return

            if os.path.isfile(file_path):
                # Detect MIME type (text/html, image/png, etc.)
                content_type, _ = mimetypes.guess_type(file_path)
                content_type = content_type or "application/octet-stream"

                with open(file_path, "rb") as f:
                    body_bytes = f.read()

                self._send_response(client_sock, 200, "OK", body_bytes, content_type)
                self._log(client_addr, method, clean_path, 200)
            else:
                # 404 Not Found
                not_found_file = os.path.join(PUBLIC_DIR, "404.html")
                if os.path.exists(not_found_file):
                    with open(not_found_file, "rb") as f:
                        body_bytes = f.read()
                else:
                    body_bytes = b"<h1>404 Not Found</h1>"

                self._send_response(client_sock, 404, "Not Found", body_bytes, "text/html")
                self._log(client_addr, method, clean_path, 404)

        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            client_sock.close()

    def _send_response(
        self,
        sock: socket.socket,
        status_code: int,
        reason: str,
        body: bytes,
        content_type: str,
    ):
        """Constructs and transmits the raw HTTP response wire packet."""
        headers = [
            f"HTTP/1.1 {status_code} {reason}",
            f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}",
            f"Server: {SERVER_NAME}",
            f"Content-Type: {content_type}; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
            "",  # Empty line separates headers from body in HTTP/1.1
            "",
        ]
        header_bytes = "\r\n".join(headers).encode("utf-8")
        sock.sendall(header_bytes + body)

    def _log(self, addr: tuple, method: str, path: str, code: int):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "\033[92m" if code == 200 else "\033[91m"
        reset = "\033[0m"
        print(f"[{timestamp}] {addr[0]}:{addr[1]}  {method:<4} {path:<18} -> {color}{code}{reset}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = RawHTTPServer(host="127.0.0.1", port=port)
    server.start()
