import ccxt
import pandas as pd
import AlphaInsider as ai
import matplotlib.pyplot as plt
import os, time
from typing import Union
from ta.trend import sma_indicator as sma
from ta.momentum import rsi
from dotenv import load_dotenv

load_dotenv()

bb_key = os.getenv('BYBIT_KEY')
bb_secret = os.getenv('BYBIT_SECRET')
ai_key = os.getenv('ALPHAINSIDER_API')

class Chart:
    def __init__(self, exchange_id='bybit', chart='BTC/USDT', timeframe='1m', limit=None, start=None, end=None):
        self.exchange_id = exchange_id
        if exchange_id == 'bybit':
            self.exchange = ccxt.bybit({'apiKey': bb_key, 'secret': bb_secret})
        elif exchange_id == 'alphainsider':
            # self.exchange = ai.exchange(ai_key)
            raise ValueError("Unsupported Exchange")
        else:
            raise ValueError(f"Unsupported Exchange: {exchange_id}")
        self.chart = chart
        self.timeframe = timeframe
        self.limit = limit
        self.start = start
        self.end = end
        self.get_historical_data()

    def get_historical_data(self):
        since = None
        if self.start:
            since = self.exchange.parse8601(self.start)

        if self.end:
            now = self.exchange.parse8601(self.end)
        else:
            now = self.exchange.milliseconds()
            self.end = int(round(time.time() * 1000))

        self.data = self.exchange.fetch_ohlcv(self.chart, self.timeframe, since, self.limit, params={'end' : self.end})

        df = pd.DataFrame(self.data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, unit='ms')
        # df.set_index('timestamp', inplace=True)
        self.df = df

        return(df)

    def plot(self):
        if self.df is not None: 
            df = self.df    
            df['close'].plot(figsize=(10, 5))
            plt.title(f"{self.chart} - {self.timeframe}")
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.show()
        else:
            raise ValueError("No data to plot. Call get_historical_data() first.")
        
    def all_data(self):
        if self.df is not None: 
            df = self.df
            return df.to_string()
        else:
            return "No data available. Call get_historical_data() first."

    def __str__(self):
        if self.df is not None: 
            df = self.df
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return str(df)
        else:
            return "No data available. Call get_historical_data() first."

class Strategy():
    def __init__(self, strategy = None, mode = 'position', investment_type = 'percentage', investment_amount = 0.1) -> None:
        self.exchange = chart.exchange
        self.mode = mode #position or signal: 'position' is good for bot only spot accounts the bot will continually check it's in the correct position. 'signal' is useful for allowing the bot to trade alongside user trades but will not correct any mistakes.
        self.investment_type = investment_type #percentage or fixed
        self.investment_amount = investment_amount #0-1 for percentage or currency amount for fixed. By default 10% of the funds in your spot account will be traded
        self.strategy = strategy #should check for valid strategy by using position or signal values like in use strategy
        
        if strategy is not None:
            self.use_strategy(strategy)

    def use_strategy(self, strategy):
        self.chart_data = strategy.chart.df
        self.strategy_data = strategy.df
        self.strategy_positions = strategy.postitions
        self.strategy_orders = strategy.orders
        self.current_positions = self.update_positions(self.exchange)
        self.strategy_signals = self.update_signals(strategy)
        # self.strategy_order = update_order(strategy) belongs in update signal function
    
    def act_strategy(self):
        if self.strategy is None:
            raise ValueError("Strategy cannot be empty, to set the strategy use the function use_strategy(strategy) to define the strategy to act on.")
        if self.mode == 'position':
            shouldHold = self.strategy_positions
            isHolding = self.current_positions
            
        elif self.mode == 'signal':
            if self.strategy_signal != 0:
                self.fill_order(self.strategy_order)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


# Defaults
SYMBOL = "BTC/USDT"
RSI_WINDOW = 7
MA_WINDOW = 5
RSIMA_WINDOW = 14
RSI_MULT = 50
RSI_OFFSET = 0
DELAYED_BUY = 1

class RSIMAX():
    # Strategy makers: the information you put in init is the values you allow your user to have control over. If your strategy is only meant for one chart on one timeframe you may decide not to take a chart variable. If your strategy works only on a single timeframe you can take in a symbol and exchange and generate the chart yourself by adding the 'from bot import Chart' line to create your own chart. 
    def __init__(self, chart, rsi_window = RSI_WINDOW, ma_window = MA_WINDOW, rsima_window = RSIMA_WINDOW, rsi_mult = RSI_MULT, rsi_offset = RSI_OFFSET, delayed_buy = DELAYED_BUY) -> None:
        self.chart = chart #should be chart type
        self.rsi_window = rsi_window
        self.ma_window = ma_window
        self.rsima_window = rsima_window
        self.rsi_mult = rsi_mult
        self.rsi_offset = rsi_offset
        self.delayed_buy = delayed_buy
        chart = self.chart
        df = chart.df
        close = df['close']
        df['ma'] = sma(close, self.ma_window)
        df['rsi'] = (rsi(close, self.rsi_window) + self.rsi_offset) * close/self.rsi_mult
        df['rsima'] = sma(df['rsi'], self.rsima_window)
        self.df = df
        self.apply_strategy()


    def __str__(self):
        if self.df is not None: 
            df = self.df
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return str(df)
        else:
            return "No data available. Call get_historical_data() first."
    
    def delay_buy(self, df=None, delayed_buy=None):
        if df is None:
            df = self.df
        if delayed_buy is None:
            delayed_buy = self.delayed_buy
        
        # Create a group ID for each consecutive set of True values
        group_id = (~df['position']).cumsum()

        # Get the number of True values in each group
        group_size = df.groupby(group_id)['position'].cumsum()

        # Set the first x True values to False in each group
        df.loc[group_size <= delayed_buy, 'position'] = False

        # Save the resulting dataframe
        # self.df = df

        return df

    def apply_strategy(self):
        df = self.df
            
        def calculate_position(row):
            condition1 = row['rsi'] > row['ma']
            condition2 = row['rsi'] > row['rsima']

            if condition1 and condition2:
                return 1
            elif condition1 or condition2:
                return 0.5
            else:
                return 0

        df['position'] = df.apply(calculate_position, axis=1)

        # print(df)
        # df['position'] = self.delay_buy(df)['position']

        # Initialize the position column to 0
        df['signal'] = 0
        
        # Set position changes
        buy_mask = (df['position'] > df['position'].shift(1, fill_value=0))
        sell_mask = (df['position'] < df['position'].shift(1, fill_value=0))
        
        df.loc[buy_mask, 'signal'] = df['position'] - df['position'].shift(1, fill_value=0)
        df.loc[sell_mask, 'signal'] = df['position'] - df['position'].shift(1, fill_value=0)

        self.df = df
        return df

    def plot(self):
        if self.df is not None:
            df = self.df.dropna().reset_index(drop=True)
            buys = df['signal'] > 0
            sells = df['signal'] < 0

            # Calculate dot sizes based on buy/sell signals
            df['dot_size'] = 0
            df.loc[buys, 'dot_size'] = df.loc[buys, 'signal'] * 50
            df.loc[sells, 'dot_size'] = -df.loc[sells, 'signal'] * 50

            # Plot the data
            df['ma'].plot(figsize=(20, 15))
            df['rsi'].plot()
            df['rsima'].plot()

            # Add green dots for buy signals
            plt.scatter(df[buys].index, df[buys]['low'], s=df.loc[buys, 'dot_size'], color='g')
            # Add red dots for sell signals
            plt.scatter(df[sells].index, df[sells]['high'], s=df.loc[sells, 'dot_size'], color='r')

            plt.title(f"{self.chart.chart} - {self.chart.timeframe}")
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.show()
        else:
            raise ValueError("No data to plot. Call apply_strategy() first.")
    
    def backtest(self, initial_investment: float = 1000, investment_mode: str = 'percentage', investment_amount: Union[float, int] = 1):
        if investment_mode not in ["fixed", "percentage"]:
            raise ValueError("Invalid investment mode. Choose either 'fixed' or 'percentage'.")

        df = self.df.copy()
        df['holdings'] = initial_investment

        # Calculate the buy and sell trades
        df['buy_signal'] = df['signal'] > 0
        df['sell_signal'] = df['signal'] < 0

        # Initialize columns for trade calculations
        df['buy_date'] = None
        df['buy_amount'] = 0
        df['asset_amount'] = 0
        df['sell_date'] = None
        df['sell_amount'] = 0
        df['profit_loss'] = 0

        # Buy and hold calculations
        df['buy_and_hold'] = (df['close'] / df.loc[df['buy_signal'], 'close'].values[0]) * initial_investment

        # Calculate buy amounts and asset amounts
        if investment_mode == "fixed":
            df.loc[df['buy_signal'], 'buy_amount'] = investment_amount
        else:  # percentage
            df.loc[df['buy_signal'], 'buy_amount'] = df['holdings'].shift(1, fill_value=initial_investment) * investment_amount

        df.loc[df['buy_signal'], 'asset_amount'] = df.loc[df['buy_signal'], 'buy_amount'] / df.loc[df['buy_signal'], 'close']

        # Calculate sell amounts and profit/loss
        df.loc[df['sell_signal'], 'sell_amount'] = df['asset_amount'].shift(1) * df.loc[df['sell_signal'], 'close']
        df.loc[df['sell_signal'], 'profit_loss'] = df.loc[df['sell_signal'], 'sell_amount'] - df.loc[df['buy_signal'], 'buy_amount'].cumsum()

        # Update holdings
        df.loc[df['buy_signal'], 'holdings'] -= df.loc[df['buy_signal'], 'buy_amount']
        df.loc[df['sell_signal'], 'holdings'] += df.loc[df['sell_signal'], 'sell_amount']

        # Assign buy and sell dates
        df.loc[df['buy_signal'], 'buy_date'] = df.loc[df['buy_signal'], 'timestamp']
        df.loc[df['sell_signal'], 'sell_date'] = df.loc[df['sell_signal'], 'timestamp']

        # Remove rows without trades
        trades_df = df.loc[df['buy_signal'] | df['sell_signal']].copy()
        trades_df.reset_index(drop=True, inplace=True)

        return trades_df

chart = Chart(timeframe="1h")
rsimax = RSIMAX(chart)
backtest = rsimax.backtest()
print(rsimax)
print(backtest)

rsimax.plot()



# buys = df[buy_mask][::-1]
        # sells = df[sell_mask][::-1]
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

    
    # def plot(self):
    #     if self.df is not None: 
    #         df = self.df.dropna().reset_index(drop=True)
    #         buys = df['signal'] > 0
    #         sells = df['signal'] < 0
    #         df['ma'].plot(figsize=(20, 15))
    #         df['rsi'].plot()
    #         df['rsima'].plot()
    #         # Add green dots for buy signals
    #         plt.scatter(df[buys].index, df[buys]['low'], color='g')
    #         # Add red dots for sell signals
    #         plt.scatter(df[sells].index, df[sells]['high'], color='r')

    #         plt.title(f"{self.chart.chart} - {self.chart.timeframe}")
    #         plt.xlabel('Date')
    #         plt.ylabel('Price')
    #         plt.show()
    #     else:
    #         raise ValueError("No data to plot. Call apply_strategy() first.")