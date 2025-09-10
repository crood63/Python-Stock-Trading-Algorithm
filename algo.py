import pandas as pd
from lumibot.backtesting import BacktestingBroker, PandasDataBacktesting
from lumibot.entities import Asset, Data
from lumibot.strategies import Strategy
from datetime import datetime
from timedelta import Timedelta 
from alpaca_trade_api import REST 
from finbert_utils import estimate_sentiment

BACKTESTING_START = datetime(2021,1,1)
BACKTESTING_END = datetime(2025,1,1)

API_KEY = "PKGPZ4HNRC89K5LW83AX"
API_SECRET = "KtBUAga230pOhjZw1oxfoZHx1Cd8NiHFPzA9nnJ5"
BASE_URL = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class MyStrategy(Strategy):
    def initialize(self):
        self.symbol = "SPY"
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = 1
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_size(self, probability, sentiment):
        cash = self.get_cash() 
        last_price = self.get_last_price(self.symbol)
        if sentiment == 'positive':
            if self.last_trade == 'sell': # case long
                if probability >= 0.75:
                    return round(cash * 1.5 / last_price,0)
                else:
                    return round(cash * 1 / last_price,0)
            else:
                return round(cash * 0.3 / last_price,0)
        elif sentiment == 'negative':
            if self.last_trade == 'buy': # case short
                if probability >= 0.75:
                    return round(cash * 1.5 / last_price,0)
                else:
                    return round(cash * 0.75 / last_price,0)
            else:
                return round(cash * 0.3 / last_price,0)
        else:
            return round(cash * 0.5 / last_price,0)
                


    def get_ema(self, window):
        bars = self.get_historical_prices(self.symbol, length=window*3).df
        ema = bars['close'].ewm(span=window, adjust=False).mean().iloc[-2]
        return ema

    def get_sma(self, window):
        bars = self.get_historical_prices(self.symbol, length=window).df
        sma = bars['close'].rolling(window=window).mean().iloc[-1]
        return sma

    def get_rsi(self, window=14):
        df = self.get_historical_prices(self.symbol, length=window*3).df
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 


    def on_trading_iteration(self):
        last_price = self.get_last_price(self.symbol)
        shortema = self.get_ema(15)
        longema = self.get_ema(50)

        # Bullish: go long
        if shortema > longema:
            if self.last_trade in ["sell", None]:
                if self.positions:
                    self.sell_all()
                probability, sentiment = self.get_sentiment() # function call placed here so that it isn't called on each iteration. Saves time
                position = self.position_size(probability, sentiment)
                if position > 0:
                    self.submit_order(
                        self.create_order(
                            self.symbol, 
                            position, 
                            "buy",                     
                            take_profit_price=last_price*1.10, 
                            stop_loss_price=last_price*0.97))
                self.last_trade = "buy"

        # Bearish: go short
        
        elif shortema < longema:
            if self.last_trade in ["buy", None]:
                if self.positions:
                    self.sell_all()
                probability, sentiment = self.get_sentiment() # function call placed here so that it isn't called on each iteration. Saves time
                position = self.position_size(probability, sentiment)
                if position > 0:
                    self.submit_order(
                        self.create_order(
                            self.symbol, 
                            position, 
                            "sell",                     
                            take_profit_price=last_price*0.93, 
                            stop_loss_price=last_price*1.03))
                self.last_trade = "sell"

if __name__ == "__main__":
    file_path = "EOD/SPY.csv"
    df = pd.read_csv(file_path)
    asset = Asset(symbol="SPY", asset_type=Asset.AssetType.STOCK)
    pandas_data = {
        asset: Data(asset, df, timestep="day"),
    }

    result = MyStrategy.run_backtest(
        PandasDataBacktesting,
        backtesting_start=datetime(2017,1,1),
        backtesting_end=datetime(2025,1,1),
        pandas_data=pandas_data
    )
