from flask import Flask, render_template
from flask_socketio import SocketIO
import json
from pymongo import MongoClient
import websocket
import threading

app = Flask(__name__)
socketio = SocketIO(app)
ws = None

# --- MongoDB Connection ---
client = MongoClient('mongodb://localhost:27017/')
db = client['upstox_data']
collection = db['live_feed']
auth_b64 = "ACCESS_TOKEN"  # Replace with your access token

# --- Upstox WebSocket Connection ---
def on_message(ws, message):
    data = json.loads(message)
    collection.insert_one(data)
    socketio.emit('live_feed', message)

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("### opened ###")
    data = {
        "guid": "someguid",
        "method": "sub",
        "data": {
            "mode": "full",
            "instrumentKeys": ["NSE_FO|45450"]
        }
    }
    ws.send(json.dumps(data))

def upstox_websocket():
    global ws
    ws = websocket.WebSocketApp(
        "wss://api.upstox.com/v2/feed/market-data-feed",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
        header={
            'Api-Version': '2.0',
            'Authorization': f'Bearer {auth_b64}'
        }
    )
    ws.run_forever()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def connect():
    print('Client connected')
    # Emit historical data in a single batch
    historical_data = list(collection.find())
    print(f"Found {len(historical_data)} historical records.")
    for data in historical_data:
        data.pop('_id')
    socketio.emit('historical_data', json.dumps(historical_data))

@socketio.on('change_security')
def change_security(instrument_key):
    global current_instrument
    print(f"Changing security to {instrument_key}")
    # Unsubscribe from the old instrument
    data = {
        "guid": "someguid",
        "method": "unsub",
        "data": {
            "instrumentKeys": [current_instrument]
        }
    }
    ws.send(json.dumps(data))
    # Subscribe to the new instrument
    data = {
        "guid": "someguid",
        "method": "sub",
        "data": {
            "mode": "full",
            "instrumentKeys": [instrument_key]
        }
    }
    ws.send(json.dumps(data))
    current_instrument = instrument_key
    # Emit historical data for the new instrument
    historical_data = list(collection.find({'feeds.' + instrument_key: {'$exists': True}}))
    print(f"Found {len(historical_data)} historical records for {instrument_key}.")
    for data in historical_data:
        data.pop('_id')
    socketio.emit('historical_data', json.dumps(historical_data))

if __name__ == '__main__':
    # Start the Upstox WebSocket client in a separate thread
    upstox_thread = threading.Thread(target=upstox_websocket)
    upstox_thread.start()
    current_instrument = "NSE_FO|45450"
    socketio.run(app, port=5003, debug=False, allow_unsafe_werkzeug=True)
