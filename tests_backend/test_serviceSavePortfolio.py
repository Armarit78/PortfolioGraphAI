from backend.portfolioGestion.ServiceSavePortfolio import ServiceSavePortfolio # type: ignore
from backend.portfolioConstruction.PortfolioFactory import Portfolio # type: ignore
from datetime import date

def test_create_portfolio():
    service = ServiceSavePortfolio()
    portfolio = Portfolio(weights={"AAPL": {"2025-01-01": 0.5}, "MSFT": {"2025-01-01": 0.5}})
    success, message = service.create_portfolio(user_email="test@gmail.com", portfolio=portfolio)
    assert message == "Portfolio created successfully"
    assert success == True

def test_create_portfolio_invalid_email():
    service = ServiceSavePortfolio()
    portfolio = Portfolio(weights={"AAPL": {str(date.today()): 0.5}, "MSFT": {str(date.today()): 0.5}})
    success, message = service.create_portfolio(user_email="invalid-email", portfolio=portfolio)
    assert success == False

def test_get_portfolio():
    service = ServiceSavePortfolio()
    success, portfolio, message = service.get_portfolio(user_email="test@gmail.com", portfolio_id=0)
    assert message == "Portfolio retrieved successfully"
    assert success == True

def test_get_portfolio_not_found():
    service = ServiceSavePortfolio()
    success, portfolio, message = service.get_portfolio(user_email="test@gmail.com", portfolio_id=999)
    assert success == False

def test_get_portfolio_wrong_user():
    service = ServiceSavePortfolio()
    success, portfolio, message = service.get_portfolio(user_email="aaa", portfolio_id=0)
    assert success == False

def test_get_portfolios_list():
    service = ServiceSavePortfolio()
    success, ids, message = service.get_portfolios_list(user_email="test@gmail.com")
    assert message == "Portfolios retrieved successfully"
    assert success == True
    assert len(ids) > 0
    assert ids[0] == 0


def test_delete_portfolio():
    service = ServiceSavePortfolio()
    success, ids, message = service.get_portfolios_list(user_email="test@gmail.com")
    for portfolio_id in ids:
        success, message = service.delete_portfolio(email="test@gmail.com", portfolio_id=portfolio_id)
        assert message == "Portfolio deleted successfully"
        assert success == True

def test_delete_portfolio_not_found():
    service = ServiceSavePortfolio()
    success, message = service.delete_portfolio(email="test@gmail.com", portfolio_id=999)
    assert success == False
