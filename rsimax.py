import datetime
import pandas as pd
import ByBit as bb
import AlphaInsider as ai
import YahooFinance as yf

current_time = datetime.datetime.utcnow()
yesterday_time = current_time - datetime.timedelta(hours=24)
pd.set_option('mode.chained_assignment', None)

#CONSTANTS
MA_LENGTH = 10
RSI_LENGTH = 7
RSI_OFFSET = 0
RSI_MULT = 50
DELAYED_BUY = 0

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

def rsimax_strategy(data):
    data['RSI'] = (rsi(data, RSI_LENGTH) + RSI_OFFSET) * data['Close']/RSI_MULT
    data['MA'] = data.Close.rolling(window=MA_LENGTH).mean()
    MA = data['MA']
    RSI = data['RSI']

    for i, ma in enumerate(MA) :  
        if ma > RSI[i] :
            data.loc[i, 'Holding'] = False
        else :
            data.loc[i, 'Holding'] = True
        if i > 0 :
            if data.loc[i, 'Holding'] != data.loc[i-1, 'Holding'] :
                if data.loc[i, 'Holding'] :
                    data.loc[i, 'Position'] = 1
                else :
                    data.loc[i, 'Position'] = -1
            else :
                data.loc[i, 'Position'] = 0
    # print(data)
    return data

def update() :
    if ai.getOrders(RSIMAX_ID).__len__() > 0:
        return "Waiting for order to complete"
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
        data = bb.get_history(stock, interval=15) #Should be pulling data from same source, however AlphaInsider is not great history data as of now
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

        bb_balance = float(bb.get_asset('ETH')['free'])

        if bb_balance > 0 :
            bbHolding = True
        else :
            bbHolding = False

        print(f"Holding {stocks[i]}:{bbHolding}, Should Hold: {shouldHold}")
        for j in range(0, DELAYED_BUY) :
            index = holding.__len__() -1 - j

            if holding[index] != holding[index-1] :
                break
        else:
            if shouldHold and not isHolding:
                ai.buyPosition(RSIMAX_ID, ids[i], amount_buy)
            if shouldHold and not bbHolding:
                print(f"Buying {stocks[i]} {amount_buy} @ {data.loc[holding.__len__()-1, 'Close']}")
        if not shouldHold and isHolding:
            ai.sellPosition(RSIMAX_ID, ids[i], stock_balance)
        if not shouldHold and bbHolding:
            print(f"Selling {stocks[i]} {stock_balance} @ {data.loc[holding.__len__()-1, 'Close']}")
            bb_order = bb.sell_order(BYBIT_AMOUNT*bb_balance, "ETHUSDT")
            print(bb_order.content)

def updateBB():
    data = bb.get_history("ETHUSDT", interval=15)
    # if error post?
    data = data.iloc[::-1].reset_index(drop=True)
    data = rsimax_strategy(data)

    stocks = [BTC]
    ids = ['ETH']
    
    
        
ai.deleteAllOrders(RSIMAX_ID)
update()