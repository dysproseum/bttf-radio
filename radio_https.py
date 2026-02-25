#import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
from email.utils import formatdate
from urllib.parse import urlparse, parse_qs
from plexapi.server import PlexServer
from dotenv import load_dotenv
import os
import random
import json

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

  def get_segments(self):
    parsed_path = urlparse(self.path)
    path_segments = parsed_path.path.strip('/').split('/')
    return path_segments

  def get_year(self):
    path_segments = self.get_segments()
    if len(path_segments) > 1 and path_segments[0] == 'year':
      return path_segments[1]
    else:
      return self.get_param('y')

  def do_GET(self):
    # Get param for year
    year = self.get_year()
    if year is None:
      self.send_response(500)
      self.end_headers()
      self.wfile.write(f"<h1>No year specified</h1>".encode())
      return
    #self.wfile.write(f"<h1>Current Year: {year}</h1>".encode())
    year = int(year)
    print(f"Year: {year}")

    # Query for songs
    plex = PlexServer(baseurl, token)
    music = plex.library.section(library)
    results = []
    results = music.search(year=year)
    print(f"Results for {year}: {len(results)}")

    # Retry if no results
    while len(results) < 1 and year > 1900:
      year -= 1
      results = music.search(year=year)
      print(f"Results for {year}: {len(results)}")

    if len(results) == 0:
      self.send_response(404)
      self.end_headers()
      return

    # Set response status code and headers
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.send_header("Access-Control-Allow-Origin", "*")
    #self.send_header('Date', formatdate(time.time(), usegmt=True))
    self.end_headers()

    urls = []
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
                #self.wfile.write(f"{track.getStreamURL()}".encode())
                urls.append(track.getStreamURL())

    random.shuffle(urls)
    self.wfile.write(json.dumps(urls).encode())

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
