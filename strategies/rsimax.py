from .. bot import Chart
from ta.trend import sma_indicator as sma
from ta.momentum import rsi


# Defaults
SYMBOL = "BTC/USDT"
RSI_WINDOW = 7
MA_WINDOW = 5
RSIMA_WINDOW = 5
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

    def apply_strategy(self):
        chart = self.chart
        df = chart.df
        close = df['close']
        df['ma'] = sma(close, self.ma_window)
        df['rsi'] = (rsi(close, self.rsi_window) + self.rsi_offset) * close/self.rsi_mult
        df['rsima'] = sma(df['rsi'], self.rsima_window)

        print(df)

chart = Chart()
print(chart)
rsimax = RSIMAX(chart)
rsimax.apply_strategy()