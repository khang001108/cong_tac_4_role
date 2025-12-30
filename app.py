from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json

# ===== MQTT CONFIG =====
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CONTROL = "esp32/khazg/control"
TOPIC_STATUS  = "esp32/khazg/status"

# ===== FLASK =====
app = Flask(__name__)

# ===== MQTT CLIENT =====
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("MQTT connected:", rc)
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    print("STATUS:", msg.payload.decode())

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ===== ROUTES =====
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control", methods=["POST"])
def control_gpio():
    data = request.json
    gpio = data.get("gpio")
    value = data.get("value")

    payload = json.dumps({
        "gpio": gpio,
        "value": value
    })

    mqtt_client.publish(TOPIC_CONTROL, payload)
    return jsonify({"status": "ok"})

# ===== MAIN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
