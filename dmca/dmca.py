from flask import Flask, request, jsonify
import transmissionrpc as tm
from os.path import getmtime, isfile, join
from os import listdir
from urllib import quote

application = Flask(__name__)

COMPLETED_TORRENT_DIR = "/dmca/static/torrents/"
PUBLIC_DIR = "/torrents/"

tc = tm.Client('localhost', port=9091)

def error(msg):
	return jsonify({"success": False, "message": msg})

def success():
	return jsonify({"success": True})

def remove_stopped_torrents(raw):
	for t in raw:
		if t.status == "stopped":
			tc.remove_torrent(t.id)

def get_torrents():
	raw = tc.get_torrents()
	remove_stopped_torrents(raw)
	out = []
	for t in raw:
		if t.status in ["downloading", "checking"]:
			out.append({	"tid": int(t.id),
							"name": t.name,
							"status": t.status,
							"progress": t.progress,
							"ratio": t.ratio
						})
	out.sort(key = lambda x: -x["tid"])

	files = []
	for f in listdir(COMPLETED_TORRENT_DIR):
		fullpath = join(COMPLETED_TORRENT_DIR, f)
		if isfile(fullpath):
			files.append((fullpath, f))
	files.sort(key = lambda x: -getmtime(x[0]))

	for f in files:
		out.append({	"name": f[1],
						"progress": 100,
						"link": PUBLIC_DIR + quote(f[1]),
						"status": "done"
					})

	return out

# We only get here when running the debug application server
@application.route("/", methods=['GET'])
def index():
	return application.send_static_file('index.html')

@application.route("/add", methods=['POST'])
def add_torrent():
	try:
		tc.add_torrent(request.form['url'])
	except Exception:
		return error("Error adding torrent. Is it a valid, or have you already added it?")

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
	return jsonify(get_torrents())

if __name__ == "__main__":
	application.run(host='localhost')

