from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json, os, threading, time

app = Flask(__name__)
CORS(app)

# ===== MQTT =====
MQTT_BROKER = "broker.emqx.io"
TOPIC_CONTROL = "esp32/khazg/control"
TOPIC_STATUS  = "esp32/khazg/status"
TOPIC_ONLINE  = "esp32/khazg/online"

ESP32_ONLINE = False
LAST_SEEN = 0

# ===== DATA FILE =====
DATA_FILE = "relay_data.json"

DEFAULT_DATA = {
    "4":  {"name": "Relay GPIO 4",  "state": 0},
    "5":  {"name": "Relay GPIO 5",  "state": 0},
    "16": {"name": "Relay GPIO 16", "state": 0},
    "17": {"name": "Relay GPIO 17", "state": 0},
}

# ===== DATA UTILS =====
def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== MQTT HANDLER =====
def on_mqtt_message(client, userdata, msg):
    global ESP32_ONLINE, LAST_SEEN

    payload = msg.payload.decode()
    topic = msg.topic

    # ONLINE / OFFLINE
    if topic == TOPIC_ONLINE:
        if payload == "online":
            ESP32_ONLINE = True
            LAST_SEEN = time.time()
        return

    # RELAY STATUS
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
            save_data(db)

# ===== MQTT LOOP THREAD =====
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

@app.route("/status", methods=["GET"])
def status():
    data = load_data()
    online = ESP32_ONLINE and (time.time() - LAST_SEEN < 15)

    return jsonify({
        "esp32": "online" if online else "offline",
        "relays": data
    })

@app.route("/control", methods=["POST"])
def control():
    data = request.json
    gpio = data.get("gpio")
    value = data.get("value")

    publish.single(
        TOPIC_CONTROL,
        f"{gpio}:{value}",
        hostname=MQTT_BROKER
    )

    return {"ok": True}

@app.route("/rename", methods=["POST"])
def rename():
    data = request.json
    gpio = str(data.get("gpio"))
    name = data.get("name")

    if not name:
        return {"error": "name required"}, 400

    db = load_data()
    if gpio not in db:
        return {"error": "GPIO not found"}, 404

    db[gpio]["name"] = name
    save_data(db)

    return {"ok": True}

# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
