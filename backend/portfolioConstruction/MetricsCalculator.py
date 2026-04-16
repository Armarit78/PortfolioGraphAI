import numpy as np
import pandas
import pandas as pd


class MetricsCalculator:
    __NB_TRADING_DAY = 252
    __RF = 0.0345

    @classmethod
    def calculate_daily_log_returns(cls, prices):
        return np.log(prices/prices.shift(1)).dropna()

    @classmethod
    def calculate_daily_arithmetic_returns(cls, prices):
        return prices.pct_change().dropna()

    @classmethod
    def calculate_global_returns(cls,returns):
        return (1+returns).prod()-1

    @classmethod
    def calculate_daily_volatility(cls,daily_returns):
        return daily_returns.std()

    @classmethod
    def calculate_annual_volatility(cls,daily_volatility):
        return daily_volatility* np.sqrt(cls.__NB_TRADING_DAY)

    @classmethod
    def calculate_sharpe_ratio(cls,annual_returns,annual_volatility):
        return (annual_returns-cls.__RF)/annual_volatility

    @classmethod
    def calculate_alpha_jensen(cls,annual_returns,beta_ptf,market_annual_return):
        return annual_returns - (cls.__RF + beta_ptf * (market_annual_return - cls.__RF))

    @classmethod
    def calculate_return_correlation_matrix(cls,historic_prices:pandas.DataFrame):
        return_matrix = np.array([cls.calculate_daily_log_returns(historic_prices[prices]) for prices in historic_prices.columns]).T

        covariance_matrix = np.corrcoef(return_matrix,rowvar=False)
        return return_matrix, covariance_matrix
