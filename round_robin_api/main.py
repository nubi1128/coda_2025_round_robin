# main.py
from flask import Flask, request, jsonify
import requests
import socket
import logging
import itertools
import threading
import time

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger()

app = Flask(__name__)

REFRESH_INTERVAL = 5  # seconds

app_servers = []
server_cycle = None
app_server_size = 0
last_server_index = 0
server_lock = threading.Lock()

# Initial discover app server
def discover_app_servers():
    try:
        infos = socket.getaddrinfo("app-api", 5000, proto=socket.IPPROTO_TCP)
        ips = sorted(set(info[4][0] for info in infos))
        logger.info(f"Discovered app-api pods: {ips}")
        return [f"http://{ip}:5000/payload" for ip in ips]
    except Exception as e:
        logger.info(f"Discovery failed: {e}")
        return []

# Background thread to refresh server list
def periodic_discovery():
    global app_servers, server_cycle, app_server_size, last_server_index
    logger.info("🟢 Starting background discovery thread")
    while True:
        time.sleep(REFRESH_INTERVAL)
        try:
            new_servers = discover_app_servers()
            if sorted(new_servers) != sorted(app_servers):
                with server_lock:
                    app_servers = new_servers
                    server_cycle = itertools.cycle(app_servers)
                    app_server_size = len(app_servers)
                    last_server_index = app_server_size - 1
                    logger.info("🔁 Refreshed app servers: %s", app_servers)
        except Exception as e:
            logger.error("❌Periodic discovery failed: %s", e)

@app.before_first_request
def startup_event():
    global app_servers, server_cycle, app_server_size, last_server_index
    app_servers = discover_app_servers()
    server_cycle = itertools.cycle(app_servers)
    app_server_size = len(app_servers)
    last_server_index = app_server_size - 1
    threading.Thread(target=periodic_discovery, daemon=True).start()

@app.route("/route", methods=["POST"])
def route():
    global last_server_index

    try:
        data = request.get_json(force=True)
    except Exception as e:
        logger.error(f"Failed to parse request: {repr(e)}")
        return jsonify({"error": "Invalid JSON"}), 400

    for _ in range(app_server_size):
        try:
            with server_lock:
                target = next(server_cycle)
                index = app_servers.index(target)
                expected_index = (last_server_index + 1) % app_server_size
                if index != expected_index:
                    logger.error(f"⚠️ Unexpected round-robin order: expected {expected_index} but got {index}")
                    raise RuntimeError(f"❌❌ Round-robin violation: expected {expected_index}, got {index}")
                logger.info(f"Routing to: {target}, previous is {last_server_index}, current is {index}")
                last_server_index = index

            resp = requests.post(target, json=data, timeout=1.5)
            return jsonify(resp.json()), resp.status_code
        except Exception as e:
            logger.error(f"Error calling backend: {repr(e)}")
            continue

    return jsonify({"error": "All backend servers failed"}), 503