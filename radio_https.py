#import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
from email.utils import formatdate
from urllib.parse import urlparse, parse_qs
from plexapi.server import PlexServer
from dotenv import load_dotenv
import os

load_dotenv(override=True)
baseurl = os.getenv('PLEX_BASEURL')
token = os.getenv('PLEX_TOKEN')
library = os.getenv('PLEX_MUSIC_LIBRARY')

class DateHTTPRequestHandler(BaseHTTPRequestHandler):
  def get_param(self, key):
    parsed_path = urlparse(self.path)
    query_params = parse_qs(parsed_path.query)
    param_value = query_params.get(key, [None])[0]
    return param_value

  def do_GET(self):
    # Set response status code and headers
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.send_header("Access-Control-Allow-Origin", "*")
    #self.send_header('Date', formatdate(time.time(), usegmt=True))
    self.end_headers()

    # Get param for year
    year = self.get_param('y')
    #self.wfile.write(f"<h1>Current Year: {year}</h1>".encode())

    # Query for songs
    plex = PlexServer(baseurl, token)
    music = plex.library.section(library)
    results = music.search(year=year)
    for result in results:
      #self.wfile.write(f"<h2>{result.TYPE} result: {result.title}</h2>".encode())
      if result.TYPE == "artist":
        # get albums
        artist = music.get(result.title)
        albums = artist.albums()
        for album in albums:
          #self.wfile.write(f"<h4>album {album.title} {album.year} ({year})</h4>".encode())
          # if year matches
          if str(album.year) == str(year):
            # get tracks
            for track in album.tracks():
              for obj in track.media:
                stream_url = track.getStreamURL()
                #self.wfile.write(f"<h6>{track.trackNumber}: {track.title} {track.getStreamURL()}</h6>".encode())
                self.wfile.write(f"{track.getStreamURL()}".encode())

# Create HTTPS server
port = os.getenv('PORT')
address = os.getenv('ADDRESS')
server_address = (address, int(port))

cert_pem = os.getenv('CERT_PEM')
key_pem = os.getenv('KEY_PEM')

httpd = HTTPServer(server_address, DateHTTPRequestHandler)
httpd.socket = ssl.wrap_socket(
  httpd.socket,
  keyfile=key_pem,
  certfile=cert_pem,
  server_side=True
)

print(f"HTTPS Server running on https://{address}:{port}")
print("Press Ctrl+C to stop the server.")

try:
  httpd.serve_forever()
except KeyboardInterrupt:
  print("\nServer stopped.")
