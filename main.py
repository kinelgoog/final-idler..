import os
import time
import threading
import logging
from flask import Flask
from steam.client import SteamClient
from steam.enums import EPersonaState

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# --- Config from environment variables ---
STEAM_LOGIN    = os.environ.get("STEAM_LOGIN", "")
STEAM_PASSWORD = os.environ.get("STEAM_PASSWORD", "")
APP_IDS        = [int(x.strip()) for x in os.environ.get("APP_IDS", "730").split(",")]
PORT           = int(os.environ.get("PORT", 10000))

# --- Flask keep-alive server ---
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Steam Idler is running!", 200

@app.route("/health")
def health():
    return {"status": "ok", "idling": APP_IDS}, 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# --- Steam Idler ---
def run_steam():
    while True:
        client = SteamClient()

        @client.on("error")
        def on_error(result):
            log.error(f"Steam error: {result}")

        @client.on("connected")
        def on_connected():
            log.info("Connected to Steam CM server")

        @client.on("channel_secured")
        def on_secured():
            log.info("Channel secured, logging in...")
            client.login(username=STEAM_LOGIN, password=STEAM_PASSWORD)

        @client.on("logged_on")
        def on_logged_on():
            log.info(f"Logged in as: {client.user.name}")
            # Офлайн статус — друзья не видят что мы онлайн,
            # но часы идут и офлайн-дни не прерываются
            client.change_status(persona_state=EPersonaState.Offline)
            log.info("Status: Offline (invisible to friends)")
            log.info(f"Starting idle for App IDs: {APP_IDS}")
            client.games_played(APP_IDS)

        @client.on("disconnected")
        def on_disconnected():
            log.warning("Disconnected from Steam. Reconnecting in 30s...")

        try:
            client.connect()
            client.run_forever()
        except Exception as e:
            log.error(f"Exception in Steam client: {e}")
        
        log.info("Restarting Steam session in 30 seconds...")
        time.sleep(30)

# --- Entry point ---
if __name__ == "__main__":
    if not STEAM_LOGIN or not STEAM_PASSWORD:
        log.error("STEAM_LOGIN or STEAM_PASSWORD not set! Check environment variables.")
        exit(1)

    log.info("Starting Flask keep-alive thread...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    log.info("Starting Steam idler...")
    run_steam()
