from datetime import datetime, timedelta

from yfinance import *

class serviceGetValue:
    def __init__(self):
        pass

    def get_historical_values(self, tickers, start_date, end_date):
        # on utilise yfinance pour récupérer les données historiques
        data = download(tickers, start=start_date, end=end_date, auto_adjust=True)
        historic_prices = data["Close"]
        return historic_prices.ffill()
