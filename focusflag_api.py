from flask import Flask, request, jsonify
from pyluxafor import LuxaforFlag
from time import sleep
from datetime import datetime

import usb.backend.libusb1
import usb.core
import random
import json
import threading
import time
import logging
import requests
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("FocusFlag")

# 🔧 Forzar el backend libusb
backend = usb.backend.libusb1.get_backend(find_library=lambda x: "/usr/lib/libusb-1.0.so")
if not backend:
    raise RuntimeError("❌ No se encontró el backend libusb")

# 🧩 Clase extendida para pasar backend a pyluxafor
class CustomLuxafor(LuxaforFlag):
    def __init__(self, backend=None):
        self.backend = backend
        super().__init__()

    def find_device(self):
        return usb.core.find(
            idVendor=self.DEVICE_VENDOR_ID,
            idProduct=self.DEVICE_PRODUCT_ID,
            backend=self.backend
        )

    def setup_device(self, device):
        try:
            if device.is_kernel_driver_active(0):
                print("🔓 Detaching kernel driver...")
                device.detach_kernel_driver(0)
        except Exception as e:
            print(f"⚠️ Could not detach kernel driver: {e}")

        print("✅ Setting device configuration...")
        device.set_configuration()

# 🚀 Iniciar Flask y Luxafor
app = Flask(__name__)

# Inicializar el Luxafor Flag
#flag = LuxaforFlag()
flag = CustomLuxafor(backend=backend)

# 📌 Ruta para apagar el Luxafor
@app.route('/off', methods=['GET'])
def turn_off():
    sleep(3)
    flag.off()
    return jsonify({"status": "off", "message": "Focus Flag Off"}), 200

# 📌 Ruta para cambiar el color del Luxafor
@app.route('/color', methods=['POST'])
def set_color():
    data = request.json  # Recibir JSON con parámetros
    r = data.get("r", 0)
    g = data.get("g", 0)
    b = data.get("b", 0)

    flag.off()
    flag.do_static_colour(leds=LuxaforFlag.LED_ALL, r=r, g=g, b=b)
#    flag.do_static_colour(r=r, g=g, b=b)
    return jsonify({"status": "on", "color": (r, g, b)}), 200

# 📌 Ruta para ejecutar un patrón predefinido


@app.route('/pattern', methods=['POST'])
def set_pattern():
    data = request.json
    pattern = data.get("pattern", "police")  # Patrón por defecto

    patterns = {
        "police": LuxaforFlag.PATTERN_POLICE,
        "random": LuxaforFlag.PATTERN_RANDOM1,
    }

    if pattern in patterns:
        flag.do_pattern(patterns[pattern], 33)
        return jsonify({"status": "pattern", "pattern": pattern}), 200
    else:
        return jsonify({"error": "Patrón no válido"}), 400

# 📌 Ruta de prueba
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "FocusFlag API is running!"}), 200

@app.route('/mock/webex', methods=['GET'])
def mock_webex():
    # Simular si estás en una reunión
    in_meeting = random.choice([True, False])

    return jsonify({
        "user": "you@example.com",
        "meeting": {
            "active": in_meeting,
            "title": "Weekly Sync" if in_meeting else None,
            "start_time": "2025-03-25T14:00:00Z" if in_meeting else None
        }
    })

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(LAST_WEBEX_STATUS)


#==========

def parse_time(tstr):
    return datetime.strptime(tstr, "%H:%M").time()

def is_within_work_hours():
    now = datetime.now().time()
    start = parse_time(WORK_HOURS["start"])
    end = parse_time(WORK_HOURS["end"])
    return start <= now <= end

# Load configuration
def load_addon_config():
    try:
        with open('/data/options.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.info(f"⚠️ Could not load options.json: {e}")
        return {}

config = load_addon_config()
WEBEX_ENABLED = config.get("webex_enabled", True)
WEBEX_INTERVAL = config.get("webex_check_interval", 60)
WORK_HOURS = config.get("work_hours", {"start": "08:00", "end": "00:00"})
WEBEX_TOKEN = config.get("webex_token", "")
WEBEX_ENDPOINT = config.get("webex_endpoint", "")
LAST_WEBEX_STATUS = {
    "in_meeting": False,
    "last_checked": None,
    "luxafor_state": "off",
    "manual_control": True
}
logger.info(f"Config loaded: Enabled={WEBEX_ENABLED}, Interval={WEBEX_INTERVAL}, Work Hours={WORK_HOURS}")

def is_flag_enabled_from_homeassistant():
    try:
        ha_url = "http://supervisor"
        token = os.getenv("SUPERVISOR_TOKEN")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        resp = requests.get(f"{ha_url}/core/states/input_boolean.focus_flag_switch", headers=headers)

        logger.info(f"📥 Response from HA input_boolean: {resp.text}")

        state = resp.json()["state"]
        #logger.info(f"🧭 input_boolean.focus_flag_switch: {state}")
        return state == "on"

    except Exception as e:
        logger.warning(f"⚠️ Could not read input_boolean from HA: {e}")
        return True  # fallback = allow

def manual_toggle_loop():
    logger.info("🎚️ Starting manual toggle watcher...")
    last_state = None
    while True:
        try:
            state = is_flag_enabled_from_homeassistant()
            if state != last_state:
                last_state = state
                if state == "on":
                    logger.info("🔘 Manual toggle ON – turning ON")
                    requests.post("http://localhost:5000/color", json={"r": 0, "g": 255, "b": 0})
                else:
                    logger.info("🔘 Manual toggle OFF – turning OFF")
                    requests.get("http://localhost:5000/off")
        except Exception as e:
            logger.warning(f"⚠️ Manual toggle error: {e}")
        time.sleep(5)

def is_user_in_meeting():
    try:
        headers = {
            "Authorization": f"Bearer {WEBEX_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            "https://webexapis.com/v1/telephony/sessions",
            headers=headers
        )

        data = response.json()

        # Si hay al menos una sesión activa
        return len(data.get("items", [])) > 0

    except Exception as e:
        logger.error(f"❌ Error checking Webex meeting status: {e}")
        return False

def webex_polling_loop_deprecated():
    logger.info("📡 Starting Webex polling thread...")
    while True:
        if WEBEX_ENABLED and is_within_work_hours():
            manual_on = is_flag_enabled_from_homeassistant()
            LAST_WEBEX_STATUS["manual_control"] = manual_on

            if not manual_on:
                logger.info("🚫 Manual toggle is OFF – skipping Luxafor control")
                #LAST_WEBEX_STATUS["manual_control"] = False
                time.sleep(WEBEX_INTERVAL)
                continue

            try:
                # 🔁 Webex API call (simulación temporal)
                res = requests.get("http://localhost:5000/mock/webex")
                data = res.json()

                in_meeting = data.get("meeting", {}).get("active", False)
                LAST_WEBEX_STATUS["in_meeting"] = in_meeting
                LAST_WEBEX_STATUS["last_checked"] = datetime.utcnow().isoformat()

                if in_meeting:
                    LAST_WEBEX_STATUS["luxafor_state"] = "on"
                    LAST_WEBEX_STATUS["manual_control"] = True
                    logger.info("🟢 In meeting – turning light ON")
                    requests.post("http://localhost:5000/color", json={"r": 255, "g": 0, "b": 0})
                else:
                    LAST_WEBEX_STATUS["luxafor_state"] = "off"
                    LAST_WEBEX_STATUS["manual_control"] = True
                    logger.info("⚪ Not in meeting – turning light OFF")
                    requests.get("http://localhost:5000/off")

            except Exception as e:
                logger.error(f"❌ Error polling Webex: {e}")

        else:
            logger.info("⏳ Outside working hours or polling disabled")

        time.sleep(WEBEX_INTERVAL)

def webex_polling_loop_mock():
    logger.info("📡 Starting Webex polling thread...")
    while True:
        if WEBEX_ENABLED and is_within_work_hours():
            try:
                # 🔁 Tu llamada real a Webex va aquí
                # Simulación temporal:
                # import requests
                res = requests.get("http://localhost:5000/mock/webex")
                data = res.json()

                if data["meeting"]["active"]:
                    LAST_WEBEX_STATUS["in_meeting"] = True
                    LAST_WEBEX_STATUS["luxafor_state"] = "on"
                    LAST_WEBEX_STATUS["last_checked"] = datetime.utcnow().isoformat()

                    logger.info("🟢 In meeting – turning light ON")
                    if not is_flag_enabled_from_homeassistant():
                        requests.post("http://localhost:5000/color", json={"r": 255, "g": 0, "b": 0})
                else:
                    LAST_WEBEX_STATUS["in_meeting"] = False
                    LAST_WEBEX_STATUS["luxafor_state"] = "off"
                    LAST_WEBEX_STATUS["last_checked"] = datetime.utcnow().isoformat()

                    logger.info("⚪ Not in meeting – turning light OFF")
                    requests.get("http://localhost:5000/off")

            except Exception as e:
                logger.info(f"❌ Error polling Webex: {e}")

        time.sleep(WEBEX_INTERVAL)

def webex_polling_loop():
    logger.info("📡 Starting Webex polling thread...")

    while True:
        now = datetime.now().strftime("%H:%M")
        logger.info(f"⏰ Now: {now} | Work hours: {WORK_HOURS['start']} - {WORK_HOURS['end']}")

        if WEBEX_ENABLED and is_within_work_hours():
            try:
                headers = {
                    "Authorization": f"Bearer {WEBEX_TOKEN}",
                    "Content-Type": "application/json"
                }

                response = requests.get(WEBEX_ENDPOINT, headers=headers, timeout=10)

                logger.info(f"⬇️ Webex response: {response.status_code}")
                logger.debug(f"⬇️ Webex raw data: {response.text}")

                if response.status_code == 200:
                    data = response.json()
                    #in_meeting = data.get("meeting", {}).get("active", False)
                    status = data.get("status", "").lower()
                    in_meeting = status == "meeting"

                    LAST_WEBEX_STATUS["in_meeting"] = in_meeting
                    LAST_WEBEX_STATUS["last_checked"] = datetime.utcnow().isoformat()

                    if in_meeting:
                        logger.info("🟢 Webex says you're in a meeting (✅ Luxafor ready)")

                        try:
                            requests.post("http://localhost:5000/color", json={"r": 255, "g": 0, "b": 0}, timeout=5)
                        except Exception as e:
                            logger.warning(f"❌ Failed to turn Luxafor ON: {e}")

                    else:
                        logger.info("⚪ Webex says you're not in a meeting")

                        try:
                            requests.get("http://localhost:5000/off", timeout=5)
                        except Exception as e:
                            logger.warning(f"❌ Failed to turn Luxafor OFF: {e}")

                else:
                    logger.warning(f"⚠️ Unexpected response from Webex: {response.status_code}")

            except Exception as e:
                logger.error(f"❌ Error polling Webex: {e}")

        time.sleep(WEBEX_INTERVAL)

threading.Thread(target=webex_polling_loop, daemon=True).start()


# Ejecutar la API
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# ----------------------------------------
# Made with ❤️ for focus and flow
