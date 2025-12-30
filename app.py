from flask import Flask, request, jsonify, render_template
import paho.mqtt.publish as publish
import os

app = Flask(__name__)

MQTT_BROKER = "broker.emqx.io"
TOPIC = "esp32/khazg/control"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control", methods=["POST"])
def control():
    data = request.json
    gpio = data.get("gpio")
    value = data.get("value")

    # gửi MQTT dạng: 4:1
    msg = f"{gpio}:{value}"
    publish.single(TOPIC, msg, hostname=MQTT_BROKER)

    return jsonify({
        "status": "ok",
        "gpio": gpio,
        "value": value
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
