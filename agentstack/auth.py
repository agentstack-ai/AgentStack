from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import webbrowser
import json
import os
import threading
import socket
from pathlib import Path

import questionary
from appdirs import user_data_dir
from agentstack import log


try:
    base_dir = Path(user_data_dir("agentstack", "agency"))
    # Test if we can write to directory
    test_file = base_dir / '.test_write_permission'
    test_file.touch()
    test_file.unlink()
except (RuntimeError, OSError, PermissionError):
    # In CI or when directory is not writable, use temp directory
    base_dir = Path(os.getenv('TEMP', '/tmp'))


class AuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle the OAuth callback from the browser"""
        try:
            # Parse the query parameters
            query_components = parse_qs(urlparse(self.path).query)

            # Extract the token from query parameters
            token = query_components.get('token', [''])[0]

            if token:
                # Store the token
                base_dir.mkdir(exist_ok=True, parents=True)

                with open(base_dir / 'auth.json', 'w') as f:
                    json.dump({'bearer_token': token}, f)

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                success_html = """
                <html>
                    <body>
                        <script>
                            setTimeout(function() {
                                window.close();
                            }, 1000);
                        </script>
                        <h2>Authentication successful! You can close this window.</h2>
                    </body>
                </html>
                """
                self.wfile.write(success_html.encode())

                # Signal the main thread that we're done
                self.server.authentication_successful = True
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authentication failed: No token received')

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f'Error: {str(e)}'.encode())


def find_free_port():
    """Find a free port on localhost"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_auth_server():
    """Start the local authentication server"""
    port = find_free_port()
    server = HTTPServer(('localhost', port), AuthCallbackHandler)
    server.authentication_successful = False
    return server, port


def login():
    """Log in to AgentStack"""
    try:
        # check if already logged in
        token = get_stored_token()
        if token:
            log.success("You are already authenticated!")
            if not questionary.confirm('Would you like to log in with a different account?').ask():
                return

        # Start the local server
        server, port = start_auth_server()

        # Create server thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Open the browser to the login page
        auth_url_base = os.getenv('AGENTSTACK_AUTHORIZATION_BASE_URL', 'https://agentstack.sh')
        auth_url = f"{auth_url_base}/login?callback_port={port}"
        webbrowser.open(auth_url)

        # Wait for authentication to complete
        while not server.authentication_successful:
            pass

        # Cleanup
        server.shutdown()
        server_thread.join()

        log.success("🔐 Authentication successful! Token has been stored.")
        return True

    except Exception as e:
        log.warn(f"Authentication failed: {str(e)}", err=True)
        return False


def get_stored_token():
    """Retrieve the stored bearer token"""
    try:
        auth_path = base_dir / 'auth.json'
        if not auth_path.exists():
            return None

        with open(auth_path) as f:
            config = json.load(f)
            return config.get('bearer_token')
    except Exception:
        return None
