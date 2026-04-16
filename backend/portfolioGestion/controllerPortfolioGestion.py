import yfinance

from backend.ai.core.llm import dbg
from backend.portfolioGestion.ServiceSavePortfolio import ServiceSavePortfolio
from backend.portfolioGestion.serviceGetValue import serviceGetValue
from backend.portfolioConstruction.PortfolioFactory import Portfolio
from backend.portfolioConstruction.MetricsCalculator import MetricsCalculator

from datetime import date, datetime, timedelta
import pandas as pd

class controllerPortfolioGestion:
    def __init__(self):
        self.serviceSave = ServiceSavePortfolio()
        self.serviceGetValue = serviceGetValue()
        self.metricsCalculator = MetricsCalculator()

    def get_portfolios(self, user_email):
        print("Fetching portfolios for email: ", user_email)
        return self.serviceSave.get_portfolios_list(user_email)
    
    def get_portfolio(self, user_email, portfolio_id):
        succes, portfolio, message = self.serviceSave.get_portfolio(user_email, portfolio_id)
        if not succes:
            return False, None, message
        
        # Récupération des données historiques pour chaque ticker du portefeuille
        clean_historic_prices = self.serviceGetValue.get_historical_values(
            tickers=[w.ticker for w in portfolio.weights],
            start_date=portfolio.investment_date(),
            end_date=datetime.today().strftime("%Y-%m-%d")
        )



        portfolio_prices = portfolio.calculate_portfolio_value(clean_historic_prices)

        result_10days = self.metricsCalculator.calculate_daily_arithmetic_returns(portfolio_prices["portfolio"].iloc[-10:])
        cumulative_results_10days= result_10days.expanding().apply(self.metricsCalculator.calculate_global_returns)
        result_daily = [{"x": date.strftime("%Y-%m-%d"), "y": float(res) } for date,res in cumulative_results_10days.items()]

        result_30days = self.metricsCalculator.calculate_daily_arithmetic_returns(portfolio_prices["portfolio"].iloc[-30:])
        cumulative_results_30days = result_30days.expanding().apply(self.metricsCalculator.calculate_global_returns)
        result_monthly = [{"x": date.strftime("%Y-%m-%d"), "y": float(res)} for date, res in cumulative_results_30days.items()]

        #en realite fait le calcul depuis le début
        result_365days = self.metricsCalculator.calculate_daily_arithmetic_returns(portfolio_prices["portfolio"])
        cumulative_results_365days = result_365days.expanding().apply(self.metricsCalculator.calculate_global_returns)
        result_yearly = [{"x": date.strftime("%Y-%m-%d"), "y": float(res)} for date, res in cumulative_results_365days.items()]

        last_date:datetime= portfolio_prices.index[-1].to_pydatetime()
        year = last_date.year
        target_start = pd.Timestamp(f"{year}-01-01")
        start_idx = portfolio_prices.index.searchsorted(target_start)
        result_ytddays = self.metricsCalculator.calculate_daily_arithmetic_returns(portfolio_prices["portfolio"].iloc[start_idx:])
        cumulative_results_ytddays = result_ytddays.expanding().apply(self.metricsCalculator.calculate_global_returns)
        result_year_to_date = [{"x": date.strftime("%Y-%m-%d"), "y": float(res)} for date, res in cumulative_results_ytddays.items()]

        portfolio_data = []
        for w in portfolio.weights:
            dbg(w.ticker)
            dbg(portfolio_prices[w.ticker])
            buy_price = portfolio_prices[w.ticker].asof(max(w.historic.keys()))
            if pd.isna(buy_price):
                buy_price = portfolio_prices[w.ticker].iloc[0]
            price = portfolio_prices[w.ticker].iloc[-1]

            portfolio_data.append({"ticker":w.ticker,
                                   "name":w.name,
                                    "weight":w.weight,
                                    "unit_buy_price":float(buy_price),
                                    "unit_price":float(price),
                                    "pnl":float((price-buy_price)/buy_price)
                                    })
        
        # Calcul du total du protefeuille
        total_name = "TOTAL"
        total_ticker = "/"
        total_weight = "1"
        total_buy_price = sum([line["weight"] * line["unit_buy_price"] for line in portfolio_data])
        total_current_price = sum([line["weight"] * line["unit_price"] for line in portfolio_data])
        total_pnl = total_current_price / total_buy_price - 1
        portfolio_data.append({"ticker":total_ticker,
                                "name":total_name,
                                "weight":total_weight,
                                "unit_buy_price":float(total_buy_price),
                                "unit_price":float(total_current_price),
                                "pnl":float(total_pnl)
                                })

        dbg("portfolio_data",portfolio_data)
        dbg("result_daily",result_daily)
        dbg("result_monthly",result_monthly)
        dbg("result_yearly",result_yearly)
        dbg("result_year_to_date",result_year_to_date)
        return True, portfolio_data, result_daily, result_monthly, result_yearly, result_year_to_date, "Portfolio retrieved successfully"

    def delete_portfolio(self, user_email, portfolio_id):
        return self.serviceSave.delete_portfolio(user_email, portfolio_id)

    def create_portfolio(self, user_email, portfolio_data):
        return self.serviceSave.create_portfolio(user_email, portfolio_data)

    def save_portfolio(self, user_email, portfolio_id, portfolio):
        return self.serviceSave.save_portfolio(user_email=user_email, portfolio_id=portfolio_id, portfolio=portfolio)
    