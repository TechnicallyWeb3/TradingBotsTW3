import datetime, os
import hashlib
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BYBIT_KEY')
api_secret = os.getenv('BYBIT_SECRET')
BASE_URL = 'https://api.bybit.com/v5/order/create'

def get_request(endpoint, params = None, body = None, header = None):
    url = BASE_URL + endpoint
    return requests.get(url, params=params, json=body, headers=header).json()

def post_request(endpoint, params = None, body = None, header = None):
    url = BASE_URL + endpoint
    return requests.post(url, params=params, json=body, headers=header)

def generate_signature(api_secret, params):
    sorted_params = sorted(params.items())
    param_string = '&'.join(f'{key}={value}' for key, value in sorted_params)
    return hashlib.sha256((param_string + api_secret).encode('utf-8')).hexdigest()

def create_order(category, symbol, side, order_type, qty, price=None, time_in_force=None):
    timeStamp = int(datetime.datetime.now().timestamp() * 1000)
    recv_window = str(5000)

    post_params = {
        "category": category,
        "symbol": symbol,
        "side": side,
        "orderType": order_type,
        "qty": qty,
        "timestamp": timeStamp,
        "recvWindow": recv_window
    }

    if price:
        post_params["price"] = price
    if time_in_force:
        post_params["timeInForce"] = time_in_force

    signature = generate_signature(api_secret, post_params)
    post_params["sign"] = signature

    headers = {
        'X-BAPI-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    return post_request(POST_ORDER, post_params, headers=headers)


# Example usage
order_response = create_order(
    category='spot',
    symbol='BTCUSDT',
    side='Buy',
    order_type='Limit',
    qty='0.1',
    price='15600',
    time_in_force='PostOnly',
    order_link_id='spot-test-postonly'
)

print(order_response)
