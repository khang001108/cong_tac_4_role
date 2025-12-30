from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json
import os
import uuid

# ================= MQTT CONFIG =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CONTROL = "esp32/khazg/control"
TOPIC_STATUS  = "esp32/khazg/status"

# ================= FLASK =================
app = Flask(__name__)

# ================= MQTT CLIENT =================
mqtt_client = mqtt.Client(
    client_id=f"web_{uuid.uuid4()}",
    clean_session=True
)

def on_connect(client, userdata, flags, rc):
    print("MQTT connected, rc =", rc)
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    print("STATUS:", msg.topic, msg.payload.decode())

def on_disconnect(client, userdata, rc):
    print("MQTT disconnected, rc =", rc)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect

# 👉 connect async + loop (fire & forget)
mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

print("MQTT init done")

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control", methods=["POST"])
def control_gpio():
    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify(ok=False, error="Invalid JSON"), 400

    mqtt_client.publish(
        TOPIC_CONTROL,
        json.dumps(data),
        qos=1
    )

    return jsonify(ok=True)

@app.route("/health")
def health():
    return jsonify(web="ok")

# ================= MAIN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
