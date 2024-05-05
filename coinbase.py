import ccxt
import pandas as pd
import pandas_ta as ta
import dotenv, os, datetime, time

dotenv.load_dotenv()

api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')

# Must choose minimum 3
TRADED_ASSETS = ['BTC', 'ETH', 'MATIC', 'SOL', 'DOGE', 'LTC']
BASE_ASSET = 'USDC'
THRESHOLD_PRICE = 10 # Minimum asset price to trade, anything under considered 0

# Only works for 1d, 1h, 1m currently
TIMEFRAME = '1d'

# This code is written in a way you need to use different MA and RSI_MA lengths.
# Using the same value for MA_LENGTH and RSI_MA will result in errors.
RSI_LENGTH = 17
MA_LENGTH = 5
RSI_MA = 20
MULTIPLIER = 50
OFFSET = 0
SOURCE = 'close'
BEARISH_TRADES = False

# Initialize the Coinbase exchange
exchange = ccxt.coinbase({
    'apiKey': api_key, 
    'secret': api_secret,
    'options': {
        'createMarketBuyOrderRequiresPrice': False
    }
})

# Load the markets
markets = exchange.load_markets()

def getDataLength():
    return MA_LENGTH + RSI_LENGTH + RSI_MA + 3

def getPrice(asset):

    if asset == BASE_ASSET:
        return 1
    # Fetch ticker data for the specified symbol
    ticker = exchange.fetch_ticker(getSymbol(asset, BASE_ASSET))

    # Get the current price from the ticker data
    return ticker['last']

def getSymbol(asset, base_asset):
    return asset + "/" + base_asset

def getChart(symbol):
    # Calculate the timestamp for getDataLength() number of candles to go back
    if (TIMEFRAME == '1d') :
        since_timestamp = exchange.parse8601((datetime.datetime.now() - datetime.timedelta(days=getDataLength())).isoformat())
    if (TIMEFRAME == '1h') :
        since_timestamp = exchange.parse8601((datetime.datetime.now() - datetime.timedelta(hours=getDataLength())).isoformat())
    if (TIMEFRAME == '1m') :
        since_timestamp = exchange.parse8601((datetime.datetime.now() - datetime.timedelta(minutes=getDataLength())).isoformat())
    return exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, since=since_timestamp)

def getCharts():

    charts = []

    for asset in TRADED_ASSETS:
        # Define the symbol for Bitcoin USDC
        symbol = getSymbol(asset, BASE_ASSET)

        # Fetch OHLCV (Open, High, Low, Close, Volume) data for the symbol
        ohlcv = getChart(symbol)

        # Convert the OHLCV data into a DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # Convert timestamp to datetime format
        df.set_index('timestamp', inplace=True)  # Set timestamp as index
        df = df.rename_axis(symbol)

        charts.append(df)
        print(df.tail())

    for i, asset in enumerate(TRADED_ASSETS):
        for j in range(i + 1, len(TRADED_ASSETS)):
            df = pd.DataFrame(charts[i])

            next_asset = TRADED_ASSETS[j]
            symbol = getSymbol(asset, next_asset)
            df = df.rename_axis(symbol)
            next_df = pd.DataFrame(charts[j])

            df = df / next_df

            charts.append(df)

            print(df.tail())
    
    return charts

def applyStrategy(chart):
    # Add SMA (Simple Moving Average) to DataFrame
    chart.ta.sma(length=MA_LENGTH, append=True)

    # Calculate RSI using pandas_ta
    rsi = (ta.rsi(chart[SOURCE], length=RSI_LENGTH) - OFFSET) * chart[f'SMA_{MA_LENGTH}'] / MULTIPLIER

    # Append the modified RSI to your DataFrame
    chart['RSI_PRICE'] = rsi

    # Add RSIMA (Simple RSI Moving Average) to DataFrame
    chart.ta.sma(length=RSI_MA, append=True, close=chart['RSI_PRICE'])

    # Print the first few rows of the DataFrame
    print(chart.tail())

    return chart

def getPosition(chart):
    previous_rsi = chart.iloc[-2][f'RSI_PRICE']
    previous_sma = chart.iloc[-2][f'SMA_{MA_LENGTH}']
    previous_rsima = chart.iloc[-2][f'SMA_{RSI_MA}']

    position = 0

    if not BEARISH_TRADES:
        if previous_rsi >= previous_sma:
            position += 1
            if previous_rsi >= previous_rsima:
                position += 1
    else:
        if previous_rsi >= previous_sma:
            position += 1
        if previous_rsi >= previous_rsima:
            position += 1

    print("Position:", position)
    # pd.DataFrame().axes['name']
    chart_name = chart.axes[0].name
    symbols = chart_name.split('/')
    # print(symbols)

    asset_score = [[symbols[0], position], [symbols[1], 2 - position]]

    return asset_score

def runBot():
    trading_charts = getCharts()

    # Initialize score totals for determining strongest asset(s)
    scores = {string: 0 for string in TRADED_ASSETS}
    scores[BASE_ASSET] = 0

    for chart in trading_charts:
        chart = applyStrategy(chart)    

        for asset, score in getPosition(chart):
            scores[asset] += score
        
    print(scores)

    # Sort the dictionary items by values in descending order
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Find the highest score
    highest_score = sorted_scores[0][1]

    # Create a list of keys with the highest score
    strong_assets = [key for key, value in sorted_scores if value == highest_score]

    print(strong_assets)

    # Initialize an empty dictionary to store traded balances
    traded_balances = {}
    owned_assets = []

    # Fetch account balance
    balances = exchange.fetch_balance()

    # Iterate through all assets
    for asset, balance in balances['total'].items():
        # Check if the asset is in TRADED_ASSETS or is the BASE_ASSET
        if asset in TRADED_ASSETS or asset == BASE_ASSET:
            # Calculate the value of the asset
            asset_value = getPrice(asset) * balance
            asset_value = asset_value if asset_value > THRESHOLD_PRICE else 0

            if asset_value > 0:
                owned_assets.append(asset)

            # if asset in strong_assets:
            # check if balance > 0 and check against the strong assets list and if not in list change is needed, make change.

            # Add the asset balance and value to the dictionary
            traded_balances[asset] = {'balance': balance, 'value': asset_value}

    print(traded_balances)

    if sorted(owned_assets) != sorted(strong_assets):

        buy_assets = []
        sell_assets = []

        for asset in owned_assets:
            if asset != BASE_ASSET:
                sell_assets.append(asset)

        for asset in strong_assets:
            if asset not in owned_assets:
                buy_assets.append(asset)

        for sell in sell_assets:
            if sell != BASE_ASSET:
                exchange.create_market_sell_order(getSymbol(sell, BASE_ASSET), traded_balances[sell]['balance'])
        
        print("Selling:", sell_assets)
        time.sleep(60)
        # Fetch account balance
        balances = exchange.fetch_balance()

        base_balance = balances[BASE_ASSET]['free']

        print(base_balance)

        for buy in strong_assets:
            if buy != BASE_ASSET:
                exchange.create_market_buy_order(getSymbol(buy, BASE_ASSET), base_balance / len(strong_assets))

        print("Buying:", strong_assets)
        print(balances)

runBot()
