from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import json
from pymongo import MongoClient
import websocket
import threading
import sqlite3
app = Flask(__name__)
socketio = SocketIO(app)
ws = None
aggregated_bar = None

# --- Database Connection ---
def get_db_connection():
    conn = sqlite3.connect('trading.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- MongoDB Connection ---
client = MongoClient('mongodb://localhost:27017/')
db = client['upstox_strategy_db']
collection = db['tick_data']
auth_b64 = "ACCESS_TOKEN"  # Replace with your access token

# --- Upstox WebSocket Connection ---
def on_message(ws, message):
    global aggregated_bar
    data = json.loads(message)
    collection.insert_one(data)

    try:
        if 'fullFeed' not in data or 'marketFF' not in data['fullFeed']:
            return

        ff = data['fullFeed']['marketFF']
        ltpc = ff.get('ltpc')
        ohlc_list = ff.get('marketOHLC', {}).get('ohlc', [])
        bid_ask_quotes = ff.get('marketLevel', {}).get('bidAskQuote', [])

        ohlc_1min = next((o for o in ohlc_list if o.get('interval') == 'I1'), None)

        if not ohlc_1min or not ltpc or not ltpc.get('ltp') or not ltpc.get('ltq') or not ltpc.get('ltt'):
            return

        current_bar_ts = int(ohlc_1min['ts'])
        trade_price = float(ltpc['ltp'])
        trade_qty = int(ltpc['ltq'])

        if aggregated_bar and current_bar_ts > aggregated_bar['ts']:
            socketio.emit('footprint_data', aggregated_bar)
            aggregated_bar = None

        if not aggregated_bar:
            aggregated_bar = {
                'ts': current_bar_ts,
                'open': trade_price,
                'high': trade_price,
                'low': trade_price,
                'close': trade_price,
                'volume': 0,
                'footprint': {}
            }

        if current_bar_ts < aggregated_bar['ts']:
            return

        aggregated_bar['high'] = max(aggregated_bar['high'], trade_price)
        aggregated_bar['low'] = min(aggregated_bar['low'], trade_price)
        aggregated_bar['close'] = trade_price
        aggregated_bar['volume'] += trade_qty

        side = 'unknown'
        for quote in bid_ask_quotes:
            if trade_price == float(quote['askP']):
                side = 'buy'
                break
        if side == 'unknown':
            for quote in bid_ask_quotes:
                if trade_price == float(quote['bidP']):
                    side = 'sell'
                    break

        price_level = f"{trade_price:.2f}"
        if price_level not in aggregated_bar['footprint']:
            aggregated_bar['footprint'][price_level] = {'buy': 0, 'sell': 0}

        if side in ['buy', 'sell']:
            aggregated_bar['footprint'][price_level][side] += trade_qty

        socketio.emit('footprint_update', aggregated_bar)

    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as e:
        print(f"Error processing message: {e} - Data: {str(data)[:200]}")

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
        "wss://api.upstox.com/v3",
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

@app.route('/api/instruments')
def get_instruments():
    conn = get_db_connection()
    instruments = conn.execute('SELECT DISTINCT instrument_key FROM instruments').fetchall()
    conn.close()
    return jsonify([instrument['instrument_key'] for instrument in instruments])

@app.route('/api/oi_data/<instrument_key>')
def get_oi_data(instrument_key):
    conn = get_db_connection()
    instrument = conn.execute('SELECT name FROM instruments WHERE instrument_key = ?',
                              (instrument_key,)).fetchone()
    if instrument is None:
        conn.close()
        return jsonify({"error": "Instrument not found"}), 404

    stock = conn.execute('SELECT id FROM stocks WHERE symbol = ?', (instrument['name'],)).fetchone()
    if stock is None:
        conn.close()
        return jsonify({"error": "Stock not found for the given instrument"}), 404

    oi_data = conn.execute('SELECT call_oi, change_in_call_oi FROM oi_data WHERE stock_id = ? ORDER BY date DESC, timestamp DESC',
                           (stock['id'],)).fetchone()
    conn.close()

    if oi_data is None:
        return jsonify({"error": "OI data not found for the given stock"}), 404

    return jsonify({
        'open_interest': oi_data['call_oi'],
        'oi_change': oi_data['change_in_call_oi']
    })

@socketio.on('connect')
def connect():
    print('Client connected')
    global aggregated_bar
    if aggregated_bar:
        socketio.emit('footprint_update', aggregated_bar)

@socketio.on('change_security')
def change_security(instrument_key):
    global current_instrument, aggregated_bar
    print(f"Changing security to {instrument_key}")

    if aggregated_bar:
        socketio.emit('footprint_data', aggregated_bar)

    aggregated_bar = None

    if ws:
        # Unsubscribe from the old instrument
        unsub_data = {
            "guid": "someguid",
            "method": "unsub",
            "data": { "instrumentKeys": [current_instrument] }
        }
        ws.send(json.dumps(unsub_data))

        # Subscribe to the new instrument
        sub_data = {
            "guid": "someguid",
            "method": "sub",
            "data": { "mode": "full", "instrumentKeys": [instrument_key] }
        }
        ws.send(json.dumps(sub_data))

    current_instrument = instrument_key

@socketio.on('replay_market_data')
def replay_market_data(data):
    global aggregated_bar
    instrument_key = data['instrument_key']
    speed = int(data['speed'])
    print(f"Replaying market data for {instrument_key} with speed {speed}ms")
    historical_data = list(collection.find({'instrumentKey': instrument_key}))

    tick_count = 0
    for data in historical_data:
        try:
            if 'fullFeed' not in data or 'marketFF' not in data['fullFeed']:
                continue

            ff = data['fullFeed']['marketFF']
            ltpc = ff.get('ltpc')
            ohlc_list = ff.get('marketOHLC', {}).get('ohlc', [])
            bid_ask_quotes = ff.get('marketLevel', {}).get('bidAskQuote', [])
            ohlc_1min = next((o for o in ohlc_list if o.get('interval') == 'I1'), None)

            if not ohlc_1min or not ltpc or not ltpc.get('ltp') or not ltpc.get('ltq') or not ltpc.get('ltt'):
                continue

            current_bar_ts = int(ohlc_1min['ts'])
            trade_price = float(ltpc['ltp'])
            trade_qty = int(ltpc['ltq'])

            if aggregated_bar and current_bar_ts > aggregated_bar['ts']:
                socketio.emit('footprint_data', aggregated_bar)
                aggregated_bar = None

            if not aggregated_bar:
                aggregated_bar = {
                    'ts': current_bar_ts,
                    'open': trade_price,
                    'high': trade_price,
                    'low': trade_price,
                    'close': trade_price,
                    'volume': 0,
                    'footprint': {}
                }

            if current_bar_ts < aggregated_bar['ts']:
                continue

            aggregated_bar['high'] = max(aggregated_bar['high'], trade_price)
            aggregated_bar['low'] = min(aggregated_bar['low'], trade_price)
            aggregated_bar['close'] = trade_price
            aggregated_bar['volume'] += trade_qty

            side = 'unknown'
            for quote in bid_ask_quotes:
                if trade_price == float(quote['askP']):
                    side = 'buy'
                    break
            if side == 'unknown':
                for quote in bid_ask_quotes:
                    if trade_price == float(quote['bidP']):
                        side = 'sell'
                        break

            price_level = f"{trade_price:.2f}"
            if price_level not in aggregated_bar['footprint']:
                aggregated_bar['footprint'][price_level] = {'buy': 0, 'sell': 0}

            if side in ['buy', 'sell']:
                aggregated_bar['footprint'][price_level][side] += trade_qty

            socketio.emit('footprint_update', aggregated_bar)

            tick_count += 1
            if tick_count % 100 == 0 and speed > 0:
                socketio.sleep(speed / 1000)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as e:
            print(f"Error processing message during replay: {e} - Data: {str(data)[:200]}")


if __name__ == '__main__':
    upstox_thread = threading.Thread(target=upstox_websocket)
    upstox_thread.start()
    current_instrument = "NSE_FO|45450"
    socketio.run(app, port=5003, debug=False, allow_unsafe_werkzeug=True)