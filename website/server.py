import http.server
import socketserver
import json
import subprocess
import os

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
# The blender project root is typically the parent folder of website/
ROOT_DIR = os.path.dirname(DIRECTORY)

class VertexHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == '/api/run':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                cmd = data.get('command')
                if not cmd:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Missing command"}')
                    return
                
                print(f"Executing: {cmd}")
                
                import tempfile
                # Use a temp file for output to prevent Windows pipe deadlocks
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as f:
                    temp_name = f.name
                
                try:
                    with open(temp_name, 'w') as out_f:
                        result = subprocess.run(
                            cmd,
                            cwd=ROOT_DIR,
                            shell=True,
                            stdout=out_f,
                            stderr=subprocess.STDOUT,
                            text=True,
                            close_fds=True
                        )
                    
                    with open(temp_name, 'r', encoding='utf-8', errors='replace') as in_f:
                        stdout_str = in_f.read()
                    
                    # Also show progress in the server terminal for the developer
                    if stdout_str.strip():
                        print(f"--- Output ---\n{stdout_str.strip()}\n--------------")
                        
                finally:
                    try:
                        os.remove(temp_name)
                    except:
                        pass
                
                output = {
                    "stdout": stdout_str,
                    "stderr": "",
                    "returncode": result.returncode
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(output).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), VertexHandler) as httpd:
        print(f"🚀 Vertex Server running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        print("Server stopped.")
