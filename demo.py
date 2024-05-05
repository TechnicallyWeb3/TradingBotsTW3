# this file is going to be a working bot which uses all the
# minimal trading features to create a functional trading bot.

import ccxt
import os
from dotenv import load_dotenv

load_dotenv()
# set defaults to prevent errors
key = os.getenv('BYBIT_KEY')
secret = os.getenv('BYBIT_SECRET')

# Variable exchange so universal functions can be used
EXCHANGE = 'bybit'

# Get correct API Keys
if (EXCHANGE == 'bybit') :
    key = os.getenv('BYBIT_KEY')
    secret = os.getenv('BYBIT_SECRET') 

# exchange = ccxt.bybit({'apiKey': key, 'secret': secret}).api
exchange = getattr(ccxt, EXCHANGE)({'apiKey': key, 'secret': secret})

session = exchange.api
print(session)