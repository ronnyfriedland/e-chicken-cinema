"""
Stream video over http
"""
import io
import logging
import socketserver
from threading import Condition
from http import server

import picamera

RESOLUTION = "800x600"
FRAMERATE = 24

PORT=8000


class StreamingOutput(): # pylint: disable=R0903
    """
    Video streaming output
    """
    def __init__(self):
        """
        The constructor
        """
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        """
        Writes data into stream
        """
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    """
    HTTP streaming handler
    """
    def do_GET(self): # pylint: disable=C0103
        """
        Handle GET requests
        """
        if self.path == '/':
            self.handle_root()
        elif self.path == '/index.html':
            self.handle_index()
        elif self.path in ('/bootstrap.min.css', '/bootstrap.min.css.map'):
            self.handle_css(self.path)
        elif self.path == '/stream.mjpg':
            self.handle_stream(output)
        else:
            self.send_error(404)
            self.end_headers()

    def handle_stream(self, out_stream):
        """
        Handle stream
        """
        self.send_response(200)
        self.send_header('Age', 0)
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        try:
            while True:
                with out_stream.condition:
                    out_stream.condition.wait()
                    frame = out_stream.frame
                self.wfile.write(b'--FRAME\r\n')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', len(frame))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
        except Exception as exception:
            logging.warning('Removed streaming client %s: %s', self.client_address, str(exception))

    def handle_index(self):
        """
        Handle index.html
        """
        with open ("html/index.html", mode="r", encoding="utf-8") as index_file:
            content=index_file.read()
            content=content.encode("utf-8")
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def handle_css(self, file):
        """
        Handle css
        """
        with open ("html/" + file, mode="r", encoding="utf-8") as css_file:
            content=css_file.read()
            content=content.encode("utf-8")
        self.send_response(200)
        self.send_header('Content-Type', 'text/css')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)


    def handle_root(self):
        """
        Handle no context - forward to index.html
        """
        self.send_response(301)
        self.send_header('Location', '/index.html')
        self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """
    Streaming server implementation
    """
    allow_reuse_address = True
    daemon_threads = True



with picamera.PiCamera(resolution=RESOLUTION, framerate=FRAMERATE) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', PORT)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()
