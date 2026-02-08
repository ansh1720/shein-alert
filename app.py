import asyncio
import aiohttp
import time
import json
import os
from flask import Flask
import threading

app = Flask(__name__)

# CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961?fields=SITE&currentPage=1&pageSize=45&format=json&query=%3Arelevance&gridColumns=5&advfilter=true&platform=Desktop&showAdsOnNextPage=false&is_ads_enable_plp=true&displayRatings=true&segmentIds=&&store=shein"
CHECK_INTERVAL = 20  # SUPER FAST
DATA_FILE = "products.json"

print(f"🚀 AIOHTTP BOT: Token={bool(BOT_TOKEN)}, Channel={bool(CHANNEL_ID)}")

stored_products = {}
data_lock = threading.Lock()

@app.route("/")
def home():
    return {"status": "SHEINVERSE AIOHTTP ULTRA-FAST 🚀"}

# ASYNC STORAGE
async def load_stored():
    global stored_products
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                stored_products = json.load(f)
    except: pass

def save_stored():
    with data_lock:
        with open(DATA_FILE, "w") as f:
            json.dump(stored_products, f)

# ASYNC TELEGRAM (PARALLEL)
async def send_message(session, text):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ No Telegram creds")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text[:4096], "parse_mode": "HTML"}
    async with session.post(url, json=payload) as resp:
        print(f"📱 Sent: {resp.status}")

async def send_photo(session, caption, image_url):
    if not BOT_TOKEN or not CHANNEL_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": CHANNEL_ID, "photo": image_url, "caption": caption[:1020], "parse_mode": "HTML"}
    async with session.post(url, json=payload) as resp:
        print(f"📸 Photo: {resp.status}")

# ASYNC PROCESSOR
async def process_product(session, p):
    code = str(p.get("code", ""))
    if not code: return
    
    name = p.get("name", "")
    price = p.get("offerPrice", {}).get("value") or p.get("price", {}).get("value") or 0
    image = p.get("images", [{}])[0].get("url")
    link = "https://www.sheinindia.in" + p.get("url", "")
    
    sizes = set()
    variants = p.get("skuList") or p.get("variantOptions") or []
    for v in variants:
        size = v.get("size") or v.get("sizeName") or v.get("value")
        if size and (v.get("inStock") is True or v.get("inStock") is None):
            sizes.add(size)
    
    with data_lock:
        prev = stored_products.get(code)
        old_sizes = set(prev.get("sizes", [])) if prev else set()
    
    # NEW PRODUCT
    if code not in stored_products:
        print(f"🆕 NEW: {name}")
        with data_lock:
            stored_products[code] = {"sizes": list(sizes)}
        caption = f"🆕 <b>NEW</b>
🛍 <b>{name}</b>
💰 ₹{price}
📦 {', '.join(sizes) or 'Available'}
🔗 {link}"
        if image:
            await send_photo(session, caption, image)
        else:
            await send_message(session, caption)
    
    # UPDATES
    else:
        sold_out = old_sizes - sizes
        restocked = sizes - old_sizes
        if sold_out:
            await send_message(session, f"⚠️ <b>SOLD OUT</b>
🛍 <b>{name}</b>
❌ {', '.join(sold_out)}
🔗 {link}")
        if restocked:
            await send_message(session, f"🔥 <b>RESTOCK</b>
🛍 <b>{name}</b>
✅ {', '.join(restocked)}
🔗 {link}")
        
        with data_lock:
            stored_products[code]["sizes"] = list(sizes)

# ULTRA-FAST MAIN LOOP
async def monitor_loop():
    await load_stored()
    print("🚀 AIOHTTP MONITOR STARTED")
    
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
    timeout = aiohttp.ClientTimeout(total=8)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        while True:
            try:
                print(f"🔄 aiohttp poll... ({time.strftime('%H:%M:%S')})")
                async with session.get(API_URL) as resp:
                    data = await resp.json()
                    products = data.get("products", [])
                    print(f"📦 {len(products)} products")
                    
                    # PARALLEL PROCESSING
                    tasks = [process_product(session, p) for p in products]
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                save_stored()
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                print(f"💥 Error: {e}")
                await asyncio.sleep(5)

def run_async():
    asyncio.run(monitor_loop())

if __name__ == "__main__":
    threading.Thread(target=run_async, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
