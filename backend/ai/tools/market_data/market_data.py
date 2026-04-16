import yfinance as yf
from langchain_core.tools import tool
from numpy.random import get_state
from pydantic import BaseModel,Field

from backend.portfolioConstruction.MetricsCalculator import MetricsCalculator

#périodes proposées par l'API
VALID_PERIODS = {'1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max'}


#tool dernier prix
class LastPriceInput(BaseModel):
    symbol : str  = Field(
        ...,
        description="Le ticker boursier officiel de l'actif (ex: 'AAPL' pour Apple, 'MSFT' pour Microsoft, 'BTC-USD' pour Bitcoin)."
    )


@tool("get_last_price", args_schema=LastPriceInput)
def get_last_price(symbol:str):
    """
    Cet outil permet de récupérer le prix d'un Ticker
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.history(period="1d")

        if info is None or info.empty:
            raise Exception("pas de données trouvées sur yfinance")
        last_close = float(info["Close"].iloc[-1])

        return f"{last_close:.2f}"
    except Exception as e:
        raise Exception(f"erreur lors de la requête yfinance : {str(e)}")



#tool valeurs historiques d'un asset
class AssetHistoryInput(BaseModel):
    symbol:str = Field(
        ...,
        description="Le ticker boursier officiel de l'actif (ex: 'AAPL' pour Apple, 'MSFT' pour Microsoft, 'BTC-USD' pour Bitcoin)."
    )

    period:str = Field(
        default="1mo",
        description=f"La période souhaitée : valeurs autorisées STRICTES : {VALID_PERIODS}"
    )


@tool("get_asset_stats", args_schema=AssetHistoryInput)
def get_asset_stats(symbol:str,period:str):
    """
    Cet outil permet de récupérer les données historiques sur une période d'un symbol
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data is None or data.empty:
            raise Exception("pas de données trouvées sur yfinance")
        prices = data["Close"]

    except Exception as e:
        raise Exception(f"erreur lors de la requête yfinance : {str(e)}")

    try:
        daily_returns = MetricsCalculator.calculate_daily_log_returns(prices)
        annual_return = MetricsCalculator.calculate_global_returns(daily_returns)
        daily_vol = MetricsCalculator.calculate_daily_volatility(daily_returns)
        annual_vol = MetricsCalculator.calculate_annual_volatility(daily_vol)
        sharpe = MetricsCalculator.calculate_sharpe_ratio(annual_return, annual_vol)
        return {
            "annualized_return": f"{annual_return*100:.2f}%",
            "annualized_volatility": f"{annual_vol:.2f}",
            "annualized_sharpe": f"{sharpe:.2f}",
        }
    except Exception as e:
        raise Exception(f"erreur lors du calcul des métriques : {str(e)}")

#tool valeurs historiques d'un asset
class AssetCompareInput(BaseModel):
    symbol1:str = Field(
        ...,
        description="Le ticker boursier officiel de l'actif (ex: 'AAPL' pour Apple, 'MSFT' pour Microsoft, 'BTC-USD' pour Bitcoin)."
    )

    symbol2: str = Field(
        ...,
        description="Le ticker boursier officiel de l'actif (ex: 'AAPL' pour Apple, 'MSFT' pour Microsoft, 'BTC-USD' pour Bitcoin)."
    )

    period:str = Field(
        default="1mo",
        description=f"La période souhaitée : valeurs autorisées STRICTES : {VALID_PERIODS}"
    )


@tool("get_compare",args_schema=AssetCompareInput)
def get_compare(symbol1:str,symbol2:str,period:str):
    """
    Cet outil permet de comparer les performances historiques de deux symboles
    """
    res1:dict = get_asset_stats.invoke({"symbol":symbol1,"period":period})
    res2:dict = get_asset_stats.invoke({"symbol":symbol2,"period":period})
    return res1,res2
