"""
MES Platform — API REST simulant une interface MES.
Gere des ordres de fabrication dans PostgreSQL.

Endpoints :
  GET  /            -> page d'accueil HTML (montre la version + le pod)
  GET  /health      -> sonde readiness/liveness
  GET  /version     -> version (visualise les rollouts)
  GET  /orders      -> liste des ordres
  POST /orders      -> cree un ordre {"product": "...", "quantity": N}
"""
import os
import time
import socket
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mes")
DB_USER = os.environ.get("DB_USER", "mes")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
POD_NAME = os.environ.get("POD_NAME", socket.gethostname())


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )


def init_db(retries=10, delay=3):
    for attempt in range(1, retries + 1):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS production_orders (
                    id SERIAL PRIMARY KEY,
                    product VARCHAR(100) NOT NULL,
                    quantity INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'created',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            print(f"[init_db] Table prete (tentative {attempt})", flush=True)
            return True
        except Exception as e:
            print(f"[init_db] {attempt}/{retries} : {e}", flush=True)
            time.sleep(delay)
    return False


@app.route("/")
def home():
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>MES Platform</title>
<style>body{{font-family:sans-serif;text-align:center;margin-top:3em}}
.badge{{background:#0b7285;color:#fff;padding:.3em .8em;border-radius:1em}}</style>
</head><body>
<h1>MES Platform</h1>
<p>Interface de suivi des ordres de fabrication</p>
<p>Version <span class="badge">{APP_VERSION}</span></p>
<p>Servi par le pod : <strong>{POD_NAME}</strong></p>
<p><a href="/orders">Voir les ordres (JSON)</a> · <a href="/health">Health</a></p>
</body></html>"""


@app.route("/health")
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify(status="healthy", version=APP_VERSION, pod=POD_NAME), 200
    except Exception as e:
        return jsonify(status="unhealthy", error=str(e)), 503


@app.route("/version")
def version():
    return jsonify(version=APP_VERSION, pod=POD_NAME)


@app.route("/orders", methods=["GET"])
def list_orders():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM production_orders ORDER BY id DESC;")
    orders = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(orders=orders, count=len(orders), served_by=POD_NAME)


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(force=True)
    product = data.get("product")
    quantity = data.get("quantity")
    if not product or quantity is None:
        return jsonify(error="Champs 'product' et 'quantity' requis"), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO production_orders (product, quantity) VALUES (%s, %s) RETURNING *;",
        (product, quantity),
    )
    order = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(order=order), 201

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
