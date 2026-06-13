#!/usr/bin/env python3
"""
Web Operator Backend Server for Colony of Minds.
Spins up a lightweight local HTTP server exposing standard web page assets
and JSON REST API endpoints to run the operator pipeline.
"""

import sys
import os
import json
import time
import argparse
import urllib.parse
import sqlite3
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

# Ensure package directories are in sys.path if run directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from colony_ai.run_colony import get_operator, get_process_memory_mb
from colony_ai.colony.router import Router
from colony_ai.colony.verifier import Verifier
from colony_ai.colony.atma import Atma
from colony_ai.colony.config import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_PATH, DEFAULT_OLLAMA_API_URL
from colony_ai.memory.memory_store import MemoryStore
from colony_ai.colony.schemas import SuboperatorResponse

SCRIPT_DIR = Path(__file__).resolve().parent
WEB_CLIENT_DIR = SCRIPT_DIR / "web_client"

class ColonyWebHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Override to suppress standard HTTP request spam in terminal
        # unless running in debug mode
        pass

    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path
        
        # 1. API Endpoint: GET /api/history
        if path == "/api/history":
            self._handle_get_history(url_parsed.query)
            return
            
        # 2. API Endpoint: GET /api/stats
        elif path == "/api/stats":
            self._handle_get_stats()
            return
            
        # 3. Serve Static Files (SPA Web Client)
        else:
            self._handle_serve_static(path)

    def do_POST(self):
        path = self.path
        
        # 4. API Endpoint: POST /api/chat
        if path == "/api/chat":
            self._handle_post_chat()
            return
        else:
            self._send_json({"error": "Endpoint not found"}, 404)

    def _handle_get_history(self, query_string):
        try:
            params = urllib.parse.parse_qs(query_string)
            limit = 20
            if "limit" in params and params["limit"][0].isdigit():
                limit = int(params["limit"][0])
                
            memory = MemoryStore()
            history = memory.get_history(limit)
            self._send_json(history)
        except Exception as e:
            self._send_json({"error": f"Failed to fetch history: {e}"}, 500)

    def _handle_get_stats(self):
        try:
            memory = MemoryStore()
            db_path = memory.db_path
            
            total_runs = 0
            verified_runs = 0
            avg_latency = 0.0
            
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*), SUM(verified) FROM interaction_log")
                    row = cursor.fetchone()
                    if row:
                        total_runs = row[0] or 0
                        verified_runs = row[1] or 0
            
            # Load memory metrics from metrics log to get average latency
            workspace_root = SCRIPT_DIR.parent
            metrics_path = workspace_root / "colony_run_metrics.jsonl"
            latencies = []
            if metrics_path.exists():
                try:
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                # sum execution times
                                exec_ms = sum(data.get("execution_times_ms", {}).values())
                                latencies.append(exec_ms)
                except Exception:
                    pass
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
            
            stats = {
                "total_queries": total_runs,
                "verified_queries": verified_runs,
                "rejected_queries": total_runs - verified_runs,
                "average_latency_ms": round(avg_latency, 2),
                "peak_ram_mb": round(get_process_memory_mb(), 2),
                "atma_default_mode": "model" if DEFAULT_OLLAMA_MODEL else "template",
                "default_model": DEFAULT_OLLAMA_MODEL or "None",
                "default_api_url": DEFAULT_OLLAMA_API_URL
            }
            self._send_json(stats)
        except Exception as e:
            self._send_json({"error": f"Failed to fetch stats: {e}"}, 500)

    def _handle_post_chat(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            query = payload.get("query", "").strip()
            atma_mode = payload.get("atma_mode", "template") # 'template' or 'model'
            model_override = payload.get("model", DEFAULT_OLLAMA_MODEL)
            
            if not query:
                self._send_json({"error": "Empty query"}, 400)
                return
                
            # Execute Pipeline directly to capture intermediate steps and facts
            router = Router()
            verifier = Verifier()
            atma = Atma()
            memory = MemoryStore()
            
            t0 = time.time()
            
            # 1. Routing
            router_response = router.route(query)
            selected_ops = router_response.selected_operators
            
            # 2. Execution
            context = {"verbose": False}
            responses = []
            execution_times = {}
            
            for op_name in selected_ops:
                op_instance = get_operator(op_name)
                t_op_0 = time.time()
                try:
                    resp = op_instance.execute(query, context)
                    responses.append(resp)
                except Exception as e:
                    responses.append(SuboperatorResponse.create_error(op_name, str(e)))
                execution_times[op_name] = int((time.time() - t_op_0) * 1000)
                
            # 3. Verification
            verification_result = verifier.verify_all(responses, query, selected_ops)
            
            # Reconstruct verified responses for Atma
            verified_responses = []
            op_responses = {}
            for fact in verification_result.facts:
                op = fact.get("operator", "unknown")
                fact_clean = {k: v for k, v in fact.items() if k != "operator"}
                op_responses.setdefault(op, []).append(fact_clean)
                
            for op, facts in op_responses.items():
                orig_resp = next((r for r in responses if r.operator == op), None)
                conf = orig_resp.confidence if orig_resp else 1.0
                verified_responses.append(SuboperatorResponse(
                    operator=op,
                    success=True,
                    confidence=conf,
                    facts=facts
                ))
                
            # 4. Atma speak
            atma_context = {}
            final_output = atma.speak(
                query=query,
                verified_responses=verified_responses,
                verbose=False,
                verification_result=verification_result,
                routed_operators=selected_ops,
                model_name=model_override if atma_mode == "model" else "",
                ollama_path=DEFAULT_OLLAMA_PATH,
                context=atma_context,
                ollama_api_url=payload.get("api_url", DEFAULT_OLLAMA_API_URL)
            )
            
            # 5. Log interaction to memory
            try:
                memory.log_interaction(
                    query=query,
                    response=final_output,
                    routed_operators=selected_ops,
                    verified=verification_result.verified,
                    verified_facts=verification_result.facts
                )
            except Exception:
                pass
                
            latency_ms = (time.time() - t0) * 1000
            current_ram = get_process_memory_mb()
            
            # Formulate detailed response payload
            response_payload = {
                "query": query,
                "response": final_output,
                "latency_ms": round(latency_ms, 2),
                "memory_mb": round(current_ram, 2),
                "atma_mode": atma_context.get("atma_mode", "template"),
                "routed_operators": selected_ops,
                "verified": verification_result.verified,
                "verified_facts": verification_result.facts,
                "rejected_facts": verification_result.rejected,
                "execution_times_ms": execution_times
            }
            
            # Append to standard metrics file
            try:
                metrics_data = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "prompt_length": len(query),
                    "selected_operators": selected_ops,
                    "execution_times_ms": execution_times,
                    "memory_usage_mb": current_ram,
                    "atma_mode": atma_context.get("atma_mode", "template")
                }
                metrics_file_path = SCRIPT_DIR.parent / "colony_run_metrics.jsonl"
                with open(metrics_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(metrics_data) + "\n")
            except Exception:
                pass
                
            self._send_json(response_payload)
            
        except Exception as e:
            self._send_json({"error": f"Failed to execute chat pipeline: {e}"}, 500)

    def _handle_serve_static(self, path):
        # Default route to index.html for SPA behavior
        if path == "/" or path == "":
            file_path = WEB_CLIENT_DIR / "index.html"
        else:
            # Prevent directory traversal attacks
            safe_path = path.lstrip("/")
            file_path = (WEB_CLIENT_DIR / safe_path).resolve()
            # Verify file is inside WEB_CLIENT_DIR
            if not str(file_path).startswith(str(WEB_CLIENT_DIR)):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"403 Forbidden")
                return
                
        if not file_path.exists() or not file_path.is_file():
            # Fall back to index.html (SPA routing support)
            file_path = WEB_CLIENT_DIR / "index.html"
            if not file_path.exists():
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")
                return
                
        # Determine MIME Type
        mime_type = "text/html"
        if file_path.suffix == ".css":
            mime_type = "text/css"
        elif file_path.suffix == ".js":
            mime_type = "application/javascript"
        elif file_path.suffix == ".json":
            mime_type = "application/json"
        elif file_path.suffix == ".png":
            mime_type = "image/png"
        elif file_path.suffix == ".svg":
            mime_type = "image/svg+xml"
            
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"500 Internal Server Error: {e}".encode("utf-8"))

    def _send_json(self, data, status_code=200):
        try:
            response_bytes = json.dumps(data).encode('utf-8')
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error encoding JSON: {e}".encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description="Colony of Minds - Web Interface Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server to (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()
    
    # Create the web client directories if they don't exist
    WEB_CLIENT_DIR.mkdir(parents=True, exist_ok=True)
    
    server_address = (args.host, args.port)
    print(f"[*] Starting Colony of Minds Web Server...")
    print(f"[*] Serving web client from: {WEB_CLIENT_DIR}")
    print(f"[*] Local endpoint: http://{args.host}:{args.port}/")
    print(f"[*] Press Ctrl+C to terminate.")
    
    try:
        httpd = HTTPServer(server_address, ColonyWebHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down HTTP server...")
        httpd.server_close()
        sys.exit(0)

if __name__ == "__main__":
    main()
