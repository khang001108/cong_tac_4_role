from flask import Flask, send_from_directory
import paho.mqtt.publish as publish
import os

app = Flask(__name__)

MQTT_BROKER = "broker.emqx.io"
TOPIC = "esp32/khazg/control"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/on")
def on():
    publish.single(TOPIC, "ON", hostname=MQTT_BROKER)
    return "ON"

@app.route("/off")
def off():
    publish.single(TOPIC, "OFF", hostname=MQTT_BROKER)
    return "OFF"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
