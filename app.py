from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from helper_files.client_helper import get_latest_price
import os

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASS = os.getenv("MONGO_DB_PASS")

mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net"
client = MongoClient(mongo_url)

# Database collections
db_trades = client.trades
assets_collection = db_trades.assets_quantities

db_simulator = client.trading_simulator
rank_collection = db_simulator.rank

app = FastAPI()

# CORS configuration to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to specific domain later
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/holdings")
async def get_holdings():
    """
    Fetch current holdings from the 'assets_quantities' collection
    and return ticker, quantity, and current price.
    """
    holdings_cursor = assets_collection.find({})
    holdings = list(holdings_cursor)
    result = []

    for asset in holdings:
        ticker = asset['symbol']
        quantity = asset['quantity']

        try:
            # Get the latest price using helper function
            current_price = get_latest_price(ticker)
        except Exception as e:
            current_price = 0  # Handle errors gracefully

        result.append({
            "ticker": ticker,
            "quantity": quantity,
            "current_price": current_price
        })

    return {"holdings": result}


@app.get("/rankings")
async def get_rankings():
    """
    Fetch algorithm rankings from the 'rank' collection and return strategy names with ranks.
    """
    rankings_cursor = rank_collection.find({}, {"_id": 0, "strategy": 1, "rank": 1})
    rankings = sorted(list(rankings_cursor), key=lambda x: x['rank'])  # Sort by rank

    return {"rankings": rankings}
