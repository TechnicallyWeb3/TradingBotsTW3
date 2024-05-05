import datetime, time, os
import pandas as pd
import ByBit as bb
import AlphaInsider as ai
import plotly.graph_objects as go
import ccxt
from dotenv import load_dotenv

load_dotenv()

bb_key = os.getenv('BYBIT_KEY')
bb_secret = os.getenv('BYBIT_SECRET')

current_time = datetime.datetime.utcnow()
yesterday_time = current_time - datetime.timedelta(hours=24)
pd.set_option('mode.chained_assignment', None)

#CONSTANTS
MA_LENGTH = 10
RSI_LENGTH = 7
RSI_OFFSET = 0
RSI_MULT = 50
DELAYED_BUY = 1

DEFAULT_PERIOD = "5d"
DEFAULT_INTERVAL = "1m"
TIME_TOLERANCE = datetime.timedelta(minutes=15)

RSIMAX_ID = "-Vtr_AKsAwKBKnYJhWyaT"
UNALLOCATED = "ubfhvYUsgvMIuJPwr76My"

BYBIT_AMOUNT = 0.5 

BTC = "BTCUSDT"
ETH = "ETHUSDT"
MATIC = "MATICUSDT"

BTC_ID = "GX2GJeDPUfT0lYc0W2up4"
ETH_ID = "v1db3S4qnHXYV38GJvbvM"
MATIC_ID = "kTzdMJXd5oE601jUNNe4y"

MINIMUM = 0.00001

exchange = ccxt.bybit({'apiKey': bb_key, 'secret': bb_secret})

def rsi(data, window=RSI_LENGTH, adjust=False):
    delta = data['Close'].diff(1).dropna()
    loss = delta.copy()
    gains = delta.copy()

    gains[gains < 0] = 0
    loss[loss > 0] = 0

    gain_ewm = gains.ewm(com=window - 1, adjust=adjust).mean()
    loss_ewm = abs(loss.ewm(com=window - 1, adjust=adjust).mean())

    RS = gain_ewm / loss_ewm
    RSI = 100 - 100 / (1 + RS)

    return RSI

def remove_holding(df):
    # Create a group ID for each consecutive set of True values
    group_id = (~df['Holding']).cumsum()

    # Get the number of True values in each group
    group_size = df.groupby(group_id)['Holding'].cumsum()

    # Set the first x True values to False in each group
    df.loc[group_size <= DELAYED_BUY, 'Holding'] = False

    # Print the resulting dataframe
    return df

def rsimax_strategy(data):
    data['RSI'] = (rsi(data, RSI_LENGTH) + RSI_OFFSET) * data['Close']/RSI_MULT
    data['MA'] = data.Close.rolling(window=MA_LENGTH).mean()
    MA = data['MA']
    RSI = data['RSI']
        
    data['Holding'] = RSI > MA
    # print(data)
    data['Holding'] = remove_holding(data)['Holding']
    # Initialize the position column to 0
    data['Position'] = 0
    
    # Set position changes
    buy_mask = data['Holding'] & ~data['Holding'].shift(1, fill_value=False)
    # print(buy_mask)
    sell_mask = ~data['Holding'] & data['Holding'].shift(1, fill_value=False)
    data.loc[buy_mask, 'Position'] = 1
    data.loc[sell_mask, 'Position'] = -1
    # buys = data[buy_mask][::-1]
    # sells = data[sell_mask][::-1]
    # offset = 0
    # pl = 0
    # last_buy = int(buys.iloc[0].name)
    # last_sell = int(sells.iloc[0].name)
    # if last_buy > last_sell:
    #     offset = 1
    # # print()
    # sorted_buys = buys.reset_index()
    # sorted_sells = sells.reset_index()
    # print(len(sorted_buys))
    # print(len(sorted_sells))
    # for i in range(len(sells)):
    #     pl += sorted_sells.loc[i, 'Close'] - sorted_buys.loc[i+offset, 'Close']
    #     # print(f"Buy: {sorted_buys.loc[i+offset, 'Close']} Sell: {sorted_sells.loc[i, 'Close']}")
        
    
    # print(pl)
        
        

    return data

def update() :
    ai.deleteAllOrders(RSIMAX_ID)
    stocks = [BTC]
    ids = [BTC_ID]

    positions = ai.getPositions(RSIMAX_ID).__len__()
    open_positions = positions
    unallocated_balance = ai.getPositionBalance(RSIMAX_ID, UNALLOCATED)
    amount_buy = unallocated_balance/stocks.__len__()

    if unallocated_balance > 0.0001 and positions > 1:
        open_positions = positions - 1
        print(f"Positions:{positions} Open:{open_positions}")
        amount_buy = unallocated_balance/(stocks.__len__() - open_positions)

    

    # print(f"Open Positions: {open_positions} Unallocated Balance: {unallocated_balance}, Share: {amount_buy}")
    stock_data = []

    for stock in stocks :
        data = bb.get_history(stock, interval='D') #Should be pulling data from same source, however AlphaInsider is not great history data as of now
        # if error post?
        data = data.iloc[::-1].reset_index(drop=True)
        data = rsimax_strategy(data)

        dates = data['Date']
        last_candle = pd.Timestamp(dates[len(dates)-1] + pd.Timedelta(minutes=TIME_TOLERANCE.total_seconds()/60))        
        pd_now = pd.Timestamp.now()
        # print(f"Last Candle = {last_candle}, Now = {pd_now}")
        if last_candle > pd_now :
            stock_data.append(data)
        else :
            ai.newPost(f"Bybit data for {stock} is out of date")

    for i, data in enumerate(stock_data) :
        holding = data['Holding']
        shouldHold = holding[holding.__len__()-1]#data.loc[holding.__len__()-1, 'Holding']

        stock_balance = ai.getPositionBalance(RSIMAX_ID, ids[i])
        
        if stock_balance > 0 :
            isHolding = True
        else :
            isHolding = False

        print(f"Holding {stocks[i]}:{isHolding}, Should Hold: {shouldHold}")
        for j in range(0, DELAYED_BUY) :
            index = holding.__len__() -1 - j

            if holding[index] != holding[index-1] :
                break
        else:
            if shouldHold and not isHolding:
                return ai.buyPosition(RSIMAX_ID, ids[i], amount_buy)
        if not shouldHold and isHolding:
            return ai.sellPosition(RSIMAX_ID, ids[i], stock_balance)


def updateBB(chart = 'BTCUSDT', coin = 'BTC', stock = 'BTC/USDT', interval = 'D'):
    price = bb.get_price(chart)
    balance = bb.get_asset(coin)

    exchange.cancel_all_spot_orders(stock)

    if balance is None :
        balance = round(float(bb.get_asset('USDT')['free'])/price, 8)
        isHolding = False
    else:
        balance = float(balance['free'])
        if balance > MINIMUM:
            isHolding = True
        else:
            balance = round(float(bb.get_asset('USDT')['free'])/price, 8)
            isHolding = False

    data = bb.get_history(chart, interval=interval)
    data = data.iloc[::-1].reset_index(drop=True)
    data = rsimax_strategy(data)
    
    holding = data['Holding']        
    shouldHold = holding[holding.__len__()-1]

    print(f"Should Hold {shouldHold}, Is Holding {isHolding}")
    if shouldHold and not isHolding:
        print("Buying")
        order = exchange.create_order(stock, 'market', 'buy', balance, price)
        print(order)
    if not shouldHold and isHolding:
        print("Selling")
        order = exchange.create_order(stock, 'market', 'sell', balance)
        print(order)

def plot(chart, timeframe = 240):
    print("Plot")
    data = bb.get_history(chart, interval = timeframe, limit=500)
    data = data.iloc[::-1].reset_index(drop=True)
    data = rsimax_strategy(data)

    buys = data[data['Position'] == 1]
    sells = data[data['Position'] == -1]

    # Candlestick
    fig = go.Figure(
        data = [
            go.Candlestick(
                x = data.index,
                open = data.Open,
                high = data.High,
                low = data.Low,
                close = data.Close
            ),
            go.Scatter(
                x = data.index, 
                y = data['RSI'],
                mode = 'lines', 
                name = f'{RSI_LENGTH}RSI', 
                line = {'color': '#ff006a'}
            ),
            go.Scatter(
                x = data.index, 
                y = data['MA'],
                mode = 'lines', 
                name = f'{MA_LENGTH}SMA',
                line = {'color': '#1900ff'}
            ), 
            go.Scatter(
                x=buys.index, 
                y=buys['Close'], 
                mode='markers',
                marker=dict(color='green', size=10), 
                name='Buy'
            ),
            go.Scatter(
                x=sells.index, 
                y=sells['Close'], 
                mode='markers',
                marker=dict(color='red', size=10), 
                name='Sell'
            )
        ]
    )
            
    fig.update_layout(
        title = f'{chart} Chart',
        xaxis_title = 'Date',
        yaxis_title = 'Price',
        xaxis_rangeslider_visible = False
    )

    fig.show()

def backtest(chart, timeframe = 240, initial = 1000):
    data = bb.get_history(chart, interval = timeframe, limit=500)
    data = data.iloc[::-1].reset_index(drop=True)
    data = rsimax_strategy(data)

    data['Investment'] = initial

    buys = data[data['Position'] == 1]
    buys = buys.reset_index()
    sells = data[data['Position'] == -1]
    sells = sells.reset_index()
    print(buys)
    print(sells)
    while buys['index'][0] > sells['index'][0]:
        sells = sells.iloc[1:].reset_index(drop=True)

    first_buy = buys['Close'][0]
    print(first_buy)

    return data

updateBB()
print(update())
price = bb.get_price('BTCUSDC')
print(price)
exchange.create_order('BTC/USDC', 'limit', 'sell', 0.0001, price) 