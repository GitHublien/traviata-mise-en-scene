"""
Serveur HTTP local qui supporte les requêtes Range (HTTP 206 Partial Content).

Le module standard `python -m http.server` ne gère PAS les Range requests :
quand un navigateur demande "donne-moi la vidéo à partir de la seconde 47",
il renvoie tout depuis le début. Conséquence : impossible de chercher (seek)
dans une vidéo, elle revient toujours à zéro quand on clique dans la timeline.

Ce script résout ce problème en implémentant le support Range proprement.
"""
import http.server
import socketserver
import os
import re
import sys
import mimetypes


class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler avec support des requêtes Range (HTTP 206)."""

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.isfile(path):
            self.send_error(404, "File not found")
            return None

        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(f.fileno())
        size = fs.st_size

        range_header = self.headers.get('Range')
        if range_header:
            m = re.match(r'bytes=(\d*)-(\d*)', range_header)
            if m:
                start = int(m.group(1)) if m.group(1) else 0
                end = int(m.group(2)) if m.group(2) else size - 1
                if start >= size:
                    self.send_error(416, "Requested Range Not Satisfiable")
                    f.close()
                    return None
                end = min(end, size - 1)
                length = end - start + 1

                self.send_response(206)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(length))
                self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()

                f.seek(start)
                self._range_remaining = length
                return f

        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(size))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        if hasattr(self, '_range_remaining') and self._range_remaining is not None:
            remaining = self._range_remaining
            self._range_remaining = None
            chunk_size = 64 * 1024
            while remaining > 0:
                chunk = source.read(min(chunk_size, remaining))
                if not chunk:
                    break
                try:
                    outputfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                remaining -= len(chunk)
        else:
            try:
                super().copyfile(source, outputfile)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

    mimetypes.add_type('video/mp4', '.mp4')
    mimetypes.add_type('text/javascript', '.js')

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    class ThreadingReusableServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ThreadingReusableServer(("", port), RangeHTTPRequestHandler) as httpd:
        print(f"Serveur Range-aware sur http://localhost:{port}")
        print("Ctrl+C pour arrêter.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")


if __name__ == '__main__':
    main()
