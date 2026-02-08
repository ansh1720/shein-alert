import asyncio
import aiohttp
import time
import json
import os
from flask import Flask
import threading
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# CONFIG (same)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961?fields=SITE&currentPage=1&pageSize=45&format=json&query=%3Arelevance&gridColumns=5&advfilter=true&platform=Desktop&showAdsOnNextPage=false&is_ads_enable_plp=true&displayRatings=true&segmentIds=&&store=shein"
CHECK_INTERVAL = 30  # Even faster!

# Global state
stored_products = {}
data_lock = threading.Lock()

# ASYNC HTTP Client (3x faster than requests)
async def fetch_products(session):
    async with session.get(API_URL) as response:
        return await response.json()

# ASYNC Telegram (parallel sends)
async def send_telegram(session, method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    async with session.post(url, json=payload) as resp:
        return resp.status == 200

@app.route("/")
def home():
    return {"status": "SHEINVERSE BOT RUNNING (AIOHTTP)"}

# MAIN ASYNC LOOP
async def monitor_loop():
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=30, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        while True:
            try:
                data = await fetch_products(session)
                products = data.get("products", [])
                
                # Process in parallel
                tasks = [process_product_async(session, p) for p in products]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)

# Your process_product logic (now async)
async def process_product_async(session, p):
    # [SAME LOGIC as before, but use await send_telegram(session, "sendPhoto", payload)]
    pass  # Implement same business logic

# Start async loop in thread
def run_async_monitor():
    asyncio.run(monitor_loop())

if __name__ == "__main__":
    threading.Thread(target=run_async_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
