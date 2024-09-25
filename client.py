from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS
import json
import certifi
from urllib.request import urlopen
from pymongo import MongoClient
import logging
import time

"""
Limited to 250 API calls per day. Will be called once at 9:00 AM on every trading day to get list of trading tickers on the nasdaq 100
Will store this list in a MongoDB cluster. We'll retrieve stock data to trade from on our mongodb for every minute to not waste our API calls
"""
def call_ndaq_100():
    def get_jsonparsed_data(url):
        response = urlopen(url, cafile=certifi.where())
        data = response.read().decode("utf-8")
        return json.loads(data)
    ndaq_url = (f"https://financialmodelingprep.com/api/v3/nasdaq_constituent?apikey={FINANCIAL_PREP_API_KEY}")
    ndaq_stocks = get_jsonparsed_data(ndaq_url)

    mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@{'cluster0.0qoxq.mongodb.net'}?retryWrites=true&writeConcern=majority"
    mongo_client = MongoClient(mongo_url)
    db = mongo_client.stock_list
    ndaq100_tickers = db.ndaq100_tickers
    ndaq100_tickers.delete_many({})
    ndaq100_tickers.insert_many(ndaq_stocks)
    mongo_client.close()
        
    

def main():
    call_ndaq_100()
    """
    client = RESTClient(api_key=POLYGON_API_KEY)
    aggs = client.get_aggs("AAPL", 1, "day", "2023-01-30", "2023-02-03")

    print(aggs)
    """


if __name__ == "__main__":
    main()