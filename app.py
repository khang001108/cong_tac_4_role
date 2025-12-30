from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CONTROL = "esp32/khazg/control"
TOPIC_STATUS  = "esp32/khazg/status"

app = Flask(__name__)

mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="web_control_server"
)
mqtt_connected = False

def on_connect(client, userdata, flags, reason_code, properties):
    global mqtt_connected
    print("MQTT connected:", reason_code)
    mqtt_connected = True
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    print("STATUS:", msg.payload.decode())

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def init_mqtt():
    global mqtt_connected
    if mqtt_connected:
        return
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()

# 🔥 Flask 3.x: gọi trực tiếp
init_mqtt()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control", methods=["POST"])
def control_gpio():
    if not mqtt_connected:
        return jsonify(ok=False, error="MQTT not connected"), 503

    data = request.json
    payload = json.dumps({
        "gpio": data["gpio"],
        "value": data["value"]
    })
    mqtt_client.publish(TOPIC_CONTROL, payload)
    return jsonify(ok=True)

@app.route("/health")
def health():
    return jsonify(web="ok", mqtt=mqtt_connected)
if __name__ == "__main__":
    print("Starting Flask dev server...")
    app.run(host="0.0.0.0", port=5000, debug=True)
