from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['upstox_strategy_db']
collection = db['tick_data']
collection.delete_many({})
print("Cleared the tick_data collection.")
