from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json
import os

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CONTROL = "esp32/khazg/control"
TOPIC_STATUS  = "esp32/khazg/status"

app = Flask(__name__)

mqtt_client = mqtt.Client(client_id="web_control_server")
mqtt_connected = False

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    print("MQTT connected:", rc)
    mqtt_connected = True
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    print("STATUS:", msg.payload.decode())

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def init_mqtt():
    try:
        mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("MQTT init done (async)")
    except Exception as e:
        print("MQTT ERROR:", e)

init_mqtt()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control", methods=["POST"])
def control_gpio():
    if not mqtt_connected:
        return jsonify(ok=False, error="MQTT not connected"), 503

    data = request.json
    mqtt_client.publish(TOPIC_CONTROL, json.dumps(data))
    return jsonify(ok=True)

@app.route("/health")
def health():
    return jsonify(web="ok", mqtt=mqtt_connected)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
