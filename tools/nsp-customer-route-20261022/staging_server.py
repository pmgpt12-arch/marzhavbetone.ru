"""Local read-only public-file server; PHP endpoints cannot execute."""
import http.server, pathlib, sys, urllib.parse
root=pathlib.Path(sys.argv[1]).resolve()
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(root),**kwargs)
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/app-script.php':
            data=(root/'app.js').read_bytes();self.send_response(200);self.send_header('Content-Type','application/javascript');self.end_headers();self.wfile.write(data);return
        if path.endswith('.php') or any(x in path for x in ['products-storage','/tools/','/.git','/data/']):
            self.send_error(403,'Disabled in local staging');return
        super().do_GET()
    def do_POST(self):self.send_error(405,'No writes in local staging')
    def log_message(self,*args):pass
http.server.ThreadingHTTPServer(('127.0.0.1',int(sys.argv[2])),Handler).serve_forever()
