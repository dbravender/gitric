import os

from flask import Flask, send_from_directory
app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello 0-downtime %s World!" % os.environ.get('BLUEGREEN', 'bland')


@app.route("/parrots/<path:path>")
def parrot(path):
    return send_from_directory(os.path.join('parrots', 'parrots'), path)
