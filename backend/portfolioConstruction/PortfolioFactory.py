import json
from datetime import datetime
from pypfopt import expected_returns, risk_models
import yfinance as yf
from scipy.optimize import minimize
import numpy as np

from backend.ai.core.llm import dbg
from backend.portfolioConstruction.EquityScreener import EquityScreener
from backend.portfolioConstruction.Portfolio import Portfolio
from backend.portfolioConstruction.Weight import Weight


class PortfolioFactory:
    #TODO : dans le créateur de portefeuille ajouter date de creation en paramètre par défaut ajd
    #TODO : dans le créateur de portefeuille : argument portefeuille avec la liste des contraintes
    def __init__(self, history_period="1y",rf=0.0345,backTestMode=False):
        if not history_period in ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"]:
            raise ValueError("History period must be in : 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max")
        #les constantes pour l'optimisation
        self.__HISTORY_PERIOD = history_period
        self.__RF = rf
        self.__PRUDENT = .3
        self.__EQUILIBRE = .5
        self.__DYNAMIQUE = .75

        #TODO : mode backtest encore pertinent avec la date ?
        self.backTestMode = backTestMode

    #récupérer les données de yahoo finance
    def get_universe(self,portfolio : Portfolio)->dict:
        equity_screener = EquityScreener(constraints=portfolio.constraints_llm)
        dbg("Equity Screener : ",equity_screener)
        universe:dict = equity_screener.build_universe()
        return universe

    #récupérer les quotes d'un appel API ou d'un fichier
    def get_quotes(self,filename=None,universe:dict=None):
        if filename is not None:
            quotes = self.load_from_universe(filename)
            return quotes

        try:
            quotes = universe.get("quotes")
        except Exception as e :
            raise ValueError("universe must be a dict with quotes key")

        return quotes

    #calculer les métriques nécessaire à la construction d'un portefeuille
    def calculate_metrics(self,quotes,date:datetime=None):
        if date is None:
            date = datetime.today()
        historic_prices = self.call_api_prices(quotes,self.__HISTORY_PERIOD,date)
        return_matrix = expected_returns.mean_historical_return(historic_prices, log_returns=False)
        covariance_matrix = risk_models.risk_matrix(historic_prices)

        return historic_prices,return_matrix,covariance_matrix


    @classmethod
    def call_api_prices(cls,quote_list:list,history_period:str,date:datetime):
        dbg("Date : ", date.strftime("%Y-%m-%d"))
        dbg("History period : ",history_period)
        dbg("Quotes : ", quote_list)
        history = yf.download(
            tickers=quote_list,
            period=history_period,
            end=date.strftime("%Y-%m-%d"),
            threads=False
        )
        historic_prices = history["Close"]

        clean_historic_prices = historic_prices.ffill().bfill()
        clean_historic_prices = clean_historic_prices.dropna(axis=1,how="any")
        dbg("Clean historic prices : ", clean_historic_prices)
        return clean_historic_prices



    @staticmethod
    def load_from_universe(universe_filename):
        try:
            with open(universe_filename,"r",encoding="utf-8") as f:
                raw_data = json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found : {universe_filename}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"file {universe_filename} is not a valid JSON file") from e

        if not "quotes" in raw_data:
            raise ValueError("JSON file does not contain quotes list")
        if not isinstance(raw_data["quotes"],list):
            raise ValueError(f"quotes must be a list")
        return raw_data["quotes"]

    def sharpe_function_negative(self, weights,return_matrix,covariance_matrix):
        numerator = np.sum(return_matrix * weights) - self.__RF
        denominator = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
        return -numerator / denominator

    #Méthode d'optimisation d'un portefeuille
    def optimize(self,historic_prices,return_matrix,covariance_matrix,portfolio:Portfolio,date_construction:datetime=datetime.today()):
        # constraints manu : niveau de risque, si pas de risque on garde prudent
        risque = "Prudent"
        if "risk" in portfolio.constraints_manu:
            risque = portfolio.constraints_manu["risk"]

        match risque:
            case "Equilibré":
                risque_value = self.__EQUILIBRE
            case "Dynamique":
                risque_value = self.__DYNAMIQUE
            case _ :
                risque_value = self.__PRUDENT

        #en découle la part d'action dans le portefeuille
        constraints = ({"type":"eq","fun":lambda x : np.sum(x)-risque_value})
        bounds = tuple((0, risque_value) for _ in historic_prices.columns)
        tickers = historic_prices.columns.tolist()
        #on initialise à l'équipondération
        weights = np.ones(len(historic_prices.columns))*(risque_value/len(historic_prices.columns))
        dbg("opti : ",type(weights.T @ covariance_matrix.values @ weights))
        dbg("opti  : ",type(weights.T @ return_matrix.values))
        res =minimize(lambda w : self.sharpe_function_negative(w,return_matrix,covariance_matrix),
                      weights,
                      method="SLSQP",
                      constraints=constraints,
                      bounds=bounds,
                      )
        dbg("statut optimisation : ",res.success)
        weights_opti = np.round(res.x, 3)

        #we build weights :
        weightList : list[Weight] = []
        for i,w in enumerate(weights_opti):
            try:
                if w != 0:
                    newWeight:Weight= Weight(name = yf.Ticker(tickers[i]).info.get("longName",""),ticker=tickers[i],weight=float(w),historic={date_construction.strftime("%Y-%m-%d"):float(w)})
                    dbg("Weights : ",newWeight)
                    weightList.append(newWeight)
            except Exception as e:
                raise ValueError(f"Erreur lors de la construction du poids {w} : {str(e)}")
        #on ajoute le fond euro à la weightList :
        #on construit le portefeuille
        weightList.append(Weight(name=yf.Ticker("0P00011S3F.F").info.get("longName",""),ticker="0P00011S3F.F",weight=float(1-risque_value),historic={date_construction.strftime("%Y-%m-%d"):float(1-risque_value)}))
        portfolio.weights = weightList
        #TODO AJOUTER FONDS EURO
        return portfolio



