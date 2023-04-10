import requests, json, datetime, hmac, hashlib, os
import pandas as pd
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BYBIT_KEY')
api_secret = os.getenv('BYBIT_SECRET')
TEST_URL = 'https://api-testnet.bybit.com/v5/'
BASE_URL = 'https://api.bybit.com/v5/'

GET_CANDLES = 'market/kline'
GET_TICKERS = 'market/tickers'
GET_ORDERS = 'order/realtime'
POST_ORDER = 'order/create'
POST_CANCEL_ALL = 'order/cancel-all'
GET_POSITIONS = 'position/list'
GET_ASSETS = 'asset/transfer/query-asset-info'

SPOT = 'spot'
MARKET_ORDER = 'Market'
BUY = 'Buy'
SELL = 'Sell'

DEFAULT_CHART = 'BTCUSDT'
DEFAULT_INTERVAL = '1'

def getRequest(endpoint, params = None, body = None, header = None):
    url = BASE_URL + endpoint
    return requests.get(url, params=params, json=body, headers=header).json()

def postRequest(endpoint, params = None, body = None, header = None):
    url = BASE_URL + endpoint
    return requests.post(url, params=params, json=body, headers=header)

def generate_signature(api_secret, timeStamp, api_key, recv_window, post_params):
    sorted_post_params = dict(sorted(post_params.items()))
    raw_request_body = json.dumps(sorted_post_params, separators=(',', ':'))
    param_str = f"{timeStamp}{api_key}{recv_window}{post_params}"
    print(param_str)
    hash = hmac.new(bytes(api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
    signature = hash.hexdigest()
    return signature

def get_history(symbol = DEFAULT_CHART, category = SPOT, interval = DEFAULT_INTERVAL):
    get_params = {
    'category' : category,
    'symbol' : symbol,
    'interval' : interval
    }
    data = getRequest(GET_CANDLES, get_params)['result']['list']
    df = pd.DataFrame(data)
    df.columns = ['startTime', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'volume', 'turnover']
    df = df.astype({'openPrice': float, 'highPrice': float, 'lowPrice': float, 'closePrice': float, 'volume': float})
    # Convert the startTime column to a datetime object
    df['startTime'] = pd.to_datetime(df['startTime'], unit='ms')

    df = df.rename(columns={'startTime': 'Date',
                        'openPrice': 'Open',
                        'highPrice': 'High',
                        'lowPrice': 'Low',
                        'closePrice': 'Close',
                        'volume': 'Volume',
                        'turnover': 'Turnover'})
    
    return df

def get_current(symbol = DEFAULT_CHART, category = SPOT) :
    get_params = {
    'category' : category,
    'symbol' : symbol
    }
    #if list data exists
    data = getRequest(GET_TICKERS, get_params)['result']['list']

    return data[0]
    #else return error

def get_price(symbol = DEFAULT_CHART) :
    return float(get_current(symbol)['lastPrice'])

def get_assets(coinName = None, timeStamp = int(datetime.datetime.now().timestamp()*1000)) :
    recv_window=str(5000)
    # Required
    get_params = {
        'accountType':'SPOT',
    }
    if coinName is not None:
        get_params['coin'] = coinName
        
    payload_str = urlencode(get_params)
    param_str= str(timeStamp) + api_key + recv_window + payload_str
    hash = hmac.new(bytes(api_secret, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
    signature = hash.hexdigest()

    headers = {
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-SIGN': signature,
        'X-BAPI-TIMESTAMP': str(timeStamp),
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    return getRequest(GET_ASSETS, get_params, header=headers)

def get_asset(coinName):
    assets = get_assets(coinName)['result']['spot']['assets']
    for asset in assets:
        if asset['coin'] == coinName:
            return asset

def buy_order(amount, symbol = DEFAULT_CHART, category = "spot"):
    post_params = {
        "category": "spot",
        "symbol": symbol,
        "side": "Buy",
        "orderType": "Market",
        "qty": amount
    }

def sell_order_old(amount, symbol = DEFAULT_CHART):
    recv_window=str(5000)
    timeStamp = int(datetime.datetime.now().timestamp()*1000)

    post_params = {
        "category": "spot",
        "symbol": symbol,
        "side": "Sell",
        "orderType": "Market",
        "qty": str(amount)
    }

    payload_str = json.dumps(post_params)
    param_str= str(timeStamp) + api_key + recv_window + payload_str
    hash = hmac.new(bytes(api_secret, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
    signature = hash.hexdigest()

    headers = {
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-SIGN': signature,
        'X-BAPI-TIMESTAMP': str(timeStamp),
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    return postRequest(POST_ORDER, post_params, header=headers)

def sell_order(amount, symbol=DEFAULT_CHART):
    post_params = {
        "category": "spot",
        "symbol": symbol,
        "side": "Sell",
        "orderType": "Market",
        "qty": str(amount)
    }
    recv_window = str(5000)
    timeStamp = int(datetime.datetime.now().timestamp() * 1000)
    payload_str = json.dumps(post_params, separators=(',',':'))
    param_str= f"{str(timeStamp)}{api_key}{recv_window}{payload_str}"
    print(param_str)
    hash = hmac.new(bytes(api_secret, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
    signature = hash.hexdigest()

    headers = {
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-SIGN': signature,
        'X-BAPI-TIMESTAMP': str(timeStamp),
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    return postRequest(POST_ORDER, body = post_params, header=headers)

print(get_asset("ETH"))
print(sell_order(0.005, "ETHUSDT").json())