import picamera
import io
import logging
import socketserver
from threading import Condition
from http import server


resolution = "800x600"
framerate = 24

port=8000


class StreamingOutput():
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.handleRoot()
        elif self.path == '/index.html':
            self.handleIndex()
        elif self.path == '/bootstrap.min.css' or self.path == '/bootstrap.min.css.map':
            self.handleCss(self.path)
        elif self.path == '/stream.mjpg':
            self.handleStream(output)
        else:
            self.send_error(404)
            self.end_headers()

    def handleStream(self, output):
        self.send_response(200)
        self.send_header('Age', 0)
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        try:
            while True:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                self.wfile.write(b'--FRAME\r\n')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', len(frame))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
        except Exception as e:
            logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))

    def handleIndex(self):
        with open ("html/index.html", "r") as indexFile:
            content=indexFile.read()
            content=content.encode("utf-8")
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def handleCss(self, file):
        with open ("html/" + file, "r") as cssFile:
            content=cssFile.read()
            content=content.encode("utf-8")
        self.send_response(200)
        self.send_header('Content-Type', 'text/css')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)


    def handleRoot(self):
        self.send_response(301)
        self.send_header('Location', '/index.html')
        self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True



with picamera.PiCamera(resolution=resolution, framerate=framerate) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', port)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()
