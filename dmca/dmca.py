from flask import Flask, request, jsonify
import transmissionrpc as tm
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
from html.parser import HTMLParser
from binascii import hexlify
import multiprocessing as mp
from pathlib import Path
import requests
import shutil
import os
import re

application = Flask(__name__)

COMPLETED_TORRENT_DIR = "/dmca/static/torrents/"
INCOMPLETE_TORRENT_DIR = "/dmca/static/torrents_tmp/"
INCOMPLETE_HTTP_DIR = "/dmca/static/http_tmp/"
PUBLIC_DIR = "torrents/"
LIBGEN_HOST = "libgen.io"

tc = tm.Client('localhost', port=9091)

def error(msg):
  return jsonify({"success": False, "message": msg})

def success():
  return jsonify({"success": True})

def remove_stopped_torrents(raw):
  for t in raw:
    if t.status == "stopped":
      tc.remove_torrent(t.id)

def get_file_list():
  # Active torrents
  raw = tc.get_torrents()
  remove_stopped_torrents(raw)
  out = []
  for t in raw:
    if t.status in ["downloading", "checking"]:
      out.append({  "tid": int(t.id),
              "name": t.name,
              "status": t.status,
              "progress": t.progress,
              "ratio": t.ratio
            })
  out.sort(key = lambda x: -x["tid"])

  # Books/HTTP downloads
  files = []
  for f in os.listdir(INCOMPLETE_HTTP_DIR):
    if f.startswith("."):
      continue
    fullpath = os.path.join(INCOMPLETE_HTTP_DIR, f)
    downloaded_size = os.path.getsize(fullpath)
    full_size = max(int(f.split("_")[-1]), 1)
    progress = min(100.0 * float(downloaded_size)/float(full_size), 100.0)
    files.append((fullpath, f, progress))

  files.sort(key = lambda x: -os.path.getmtime(x[0]))
  files = files[:10]

  for f in files:
    out.append({"name": f[1],
                "progress": f[2],
                "status": "downloading"})

  # Completed files
  files = []
  for f in os.listdir(COMPLETED_TORRENT_DIR):
    fullpath = os.path.join(COMPLETED_TORRENT_DIR, f)
    # Hack, but nginx's try_files is redirecting to port 80 :/
    if os.path.isdir(fullpath):
      f += os.path.sep
    files.append((fullpath, f))
  files.sort(key = lambda x: -os.path.getmtime(x[0]))
  files = files[:10]

  for f in files:
    out.append({  "name": f[1],
            "progress": 100,
            "link": os.path.join(PUBLIC_DIR, f[1]),
            "status": "done"
          })

  return out

def download_file(url):
  r = requests.get(url, stream=True)
  disposition_header = r.headers.get("content-disposition", "")
  filename = re.findall("filename=(.+)", disposition_header)[0]
  if filename.startswith('"') and filename.endswith('"'):
    filename = filename[1:-1]
  extensions = ''.join(Path(filename).suffixes)
  filename = os.path.basename(filename) + "_" + hexlify(os.urandom(32)).decode("utf8")
  filename = filename + "_" + str(int(r.headers.get('content-length', '0')))
  full_filename = os.path.join(INCOMPLETE_HTTP_DIR, filename)
  try:
    with open(full_filename, 'wb') as fout:
      for chunk in r.iter_content(chunk_size=2048):
        if chunk:
          fout.write(chunk)
  except Exception:
    os.unlink(full_filename)
  r.close()
  outfile = os.path.join(COMPLETED_TORRENT_DIR, filename + extensions)
  shutil.move(full_filename, outfile)

def try_download_book(url):
  r = requests.get(url)
  soup = BeautifulSoup(r.text, "html.parser")
  links = soup.find_all('a')
  for link in links:
    href = link.attrs.get("href", "")
    if "key=" in href:
      h = HTMLParser()
      href = h.unescape(href)
      download_file(href)

def try_download_book_async(url):
  parsed = urlparse(url)
  if parsed.netloc == LIBGEN_HOST and parsed.scheme in ["http", "https"]:
    mp.set_executable("/usr/bin/python3")
    ctx = mp.get_context("spawn")
    p = ctx.Process(target=try_download_book, args=(url,))
    p.start()
    return True
  return False

# We only get here when running the debug application server
@application.route("/", methods=['GET'])
def index():
  return application.send_static_file('index.html')

@application.route("/add", methods=['POST'])
def add_torrent():
  if try_download_book_async(request.form['url']):
    return success()
  try:
    tc.add_torrent(request.form['url'])
  except Exception:
    return error("Error adding torrent")

  return success()

@application.route("/kill", methods=['POST'])
def kill_torrent():
  tid = request.form['tid']
  try:
    tc.stop_torrent(tid)
    tc.remove_torrent(tid)
  except Exception:
    return error("Error stopping torrent")

  return success()

@application.route("/status", methods=['GET'])
def get_status():
  return jsonify(get_file_list())

if __name__ == "__main__":
  application.run(host='localhost')

