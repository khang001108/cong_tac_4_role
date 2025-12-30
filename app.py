from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json, os, threading, time
from queue import Queue
from threading import Lock

app = Flask(__name__)
CORS(app)

# ===== MQTT =====
MQTT_BROKER = "broker.emqx.io"
TOPIC_CONTROL = "esp32/khazg/control"
TOPIC_STATUS  = "esp32/khazg/status"
TOPIC_ONLINE  = "esp32/khazg/online"

ESP32_ONLINE = False
LAST_SEEN = 0

# ===== DATA =====
DATA_FILE = "relay_data.json"
data_lock = Lock()

DEFAULT_DATA = {
    "4":  {"name": "Relay GPIO 4",  "state": 0, "on_since": None},
    "5":  {"name": "Relay GPIO 5",  "state": 0, "on_since": None},
    "16": {"name": "Relay GPIO 16", "state": 0, "on_since": None},
    "17": {"name": "Relay GPIO 17", "state": 0, "on_since": None},
}


def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            save_data(DEFAULT_DATA)
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_data(data):
    with data_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ===== SSE =====
clients = []

def push_event(payload):
    for q in clients:
        q.put(payload)

@app.route("/events")
def events():
    def stream():
        q = Queue()
        clients.append(q)
        try:
            while True:
                data = q.get()
                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            clients.remove(q)

    return Response(stream(), mimetype="text/event-stream")

# ===== MQTT CALLBACK =====
def on_mqtt_message(client, userdata, msg):
    global ESP32_ONLINE, LAST_SEEN

    payload = msg.payload.decode()
    topic = msg.topic

    if topic == TOPIC_ONLINE:
        ESP32_ONLINE = payload == "online"
        LAST_SEEN = time.time()

        if payload == "online":
            db = load_data()
            for gpio in db:
                if db[gpio]["state"] == 1:
                    db[gpio]["on_since"] = int(time.time())
            save_data(db)

        push_event({
            "type": "online",
            "status": payload
        })
        return



    if topic == TOPIC_STATUS:
        try:
            gpio, value = payload.split(":")
            gpio = str(gpio)
            value = int(value)
        except:
            return

        db = load_data()
        if gpio in db:
            db[gpio]["state"] = value

            if value == 1:
                if not db[gpio].get("on_since"):
                    db[gpio]["on_since"] = int(time.time())
            else:
                db[gpio]["on_since"] = None

            save_data(db)

            push_event({
                "type": "relay",
                "gpio": gpio,
                "state": value,
                "on_since": db[gpio]["on_since"]
            })


            
# ===== ONLINE WATCHDOG =====
def online_watchdog():
    global ESP32_ONLINE
    while True:
        time.sleep(3)
        if ESP32_ONLINE and time.time() - LAST_SEEN > 10:
            ESP32_ONLINE = False
            push_event({"type": "online", "status": "offline"})

threading.Thread(target=online_watchdog, daemon=True).start()

# ===== MQTT THREAD =====
def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_mqtt_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(TOPIC_ONLINE)
    client.subscribe(TOPIC_STATUS)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# ===== ROUTES =====
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status")
def status():
    online = ESP32_ONLINE and (time.time() - LAST_SEEN < 15)

    return jsonify({
        "esp32": "online" if online else "offline",
        "relays": load_data()
    })


@app.route("/control", methods=["POST"])
def control():
    data = request.json or {}
    gpio = str(data.get("gpio"))
    value = int(data.get("value", -1))

    if gpio not in load_data() or value not in (0, 1):
        return {"error": "invalid"}, 400

    publish.single(
        TOPIC_CONTROL,
        f"{gpio}:{value}",
        hostname=MQTT_BROKER
    )

    return {"ok": True}

@app.route("/rename", methods=["POST"])
def rename():
    data = request.json or {}
    gpio = str(data.get("gpio"))
    name = data.get("name", "").strip()

    if not name:
        return {"error": "name required"}, 400

    db = load_data()
    if gpio not in db:
        return {"error": "not found"}, 404

    db[gpio]["name"] = name
    save_data(db)

    push_event({
        "type": "rename",
        "gpio": gpio,
        "name": name
    })

    return {"ok": True}

# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)
