# FootprintChart
Using market data  Feed and MONGODB generate FOOTPrint chart
 Chart Type: A Footprint Chart (Cluster Chart) is used, which replaces traditional candlesticks with detailed volume data at each price level within a given time frame.
Volume Bubbles (Cluster Volume): Within each bar of the footprint chart, numerical values represent the volume traded at specific price points. The size or color of these "bubbles" (cells) indicates relative volume, often differentiating between aggressive buyers (asks hit) and aggressive sellers (bids hit).
Open Interest Change: A separate panel or a heatmap overlay can be used to display the change in Open Interest for specific strike prices or for the entire option contract. 

Interpretation for Options Trading
Traders combine these data points to confirm market direction and identify institutional activity. 
Bullish Signal: If price is rising, accompanied by large buy-side volume bubbles in the footprint and a significant positive change in Open Interest, it suggests new money is entering long positions, confirming the upward trend.
Bearish Signal: Conversely, falling prices with high sell-side volume and a decrease in Open Interest could indicate positions are being closed out (money flowing out), pointing to a potential reversal or exhaustion of the trend.
Key Levels: Large volume accumulation (Point of Control) visible through volume bubbles on the footprint chart, combined with high Open Interest at a specific strike, often highlights strong support or resistance zones where significant market interest exists. 

NIFTY_OptionChainData.csv and BANKNIFTY_OptionChainData.csv are option chain data file for NIFTY and BANKNIFTY.

JS LIB : echarts.min.js
BACKEND : SERVER : python FLASK APP 
DB : MONGODB
MONGO_URI = "mongodb://localhost:27017/" 
MONGO_DB_NAME = "upstox_strategy_db"
TICK_COLLECTION = "tick_data"
WSS LIVE FEED STRUCTURE :
 RECORDS in MONGODB LOOOKS LIKE BELOW  ref :
  """" :
  
 {
  "_id": {
    "$oid": "692fc4cd312afef23e6448b3"
  },
  "fullFeed": {
    "marketFF": {
      "ltpc": {
        "ltp": 3183.8,
        "ltt": "1764738254253",
        "ltq": "1",
        "cp": 3135.7
      },
      "marketLevel": {
        "bidAskQuote": [
          {
            "bidQ": "2",
            "bidP": 3183.3,
            "askQ": "67",
            "askP": 3183.8
          },
          {
            "bidQ": "85",
            "bidP": 3182.8,
            "askQ": "72",
            "askP": 3183.9
          },
          {
            "bidQ": "192",
            "bidP": 3182.7,
            "askQ": "134",
            "askP": 3184
          },
          {
            "bidQ": "26",
            "bidP": 3182.5,
            "askQ": "81",
            "askP": 3184.1
          },
          {
            "bidQ": "350",
            "bidP": 3182.4,
            "askQ": "74",
            "askP": 3184.2
          }
        ]
      },
      "optionGreeks": {},
      "marketOHLC": {
        "ohlc": [
          {
            "interval": "1d",
            "open": 3140,
            "high": 3186.8,
            "low": 3139,
            "close": 3183.8,
            "vol": "945518",
            "ts": "1764700200000"
          },
          {
            "interval": "I1",
            "open": 3184.6,
            "high": 3185.5,
            "low": 3181.6,
            "close": 3184.6,
            "vol": "8031",
            "ts": "1764738180000"
          }
        ]
      },
      "atp": 3168.99,
      "vtt": "945518",
      "tbq": 134272,
      "tsq": 234435
    }
  },
  "requestMode": "full_d5",
  "instrumentKey": "NSE_EQ|INE467B01029",
  "_insertion_time": {
    "$date": "2025-12-03T10:34:13.670Z"
  }
}
""""
