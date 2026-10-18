import os
import sqlite3
from flask import Flask, request

app = Flask(__name__)


@app.route("/search")
def search():
    term = request.args.get("q")
    cur = sqlite3.connect("app.db").cursor()
    cur.execute("SELECT * FROM items WHERE name = '" + term + "'")
    return str(cur.fetchall())


@app.route("/ping")
def ping():
    host = request.form["host"]
    os.system("ping -c 1 " + host)
    return "ok"


@app.route("/health")
def health():
    return "ok"