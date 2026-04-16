import pytest
from portfolioGestion.controllerPortfolioGestion import controllerPortfolioGestion # type: ignore


controller = controllerPortfolioGestion(serviceSavePortfolio=None)

def test_get_portfolios():
    # Arrange
    user_email = "test@gmail.com"

    # Act
    result = controller.get_portfolios(user_email)

    # Assert
    assert result is not None

def test_save_portfolio():
    # Arrange
    user_email = "test@gmail.com"
    portfolio_data = {"name": "Test Portfolio", "assets": []}

    # Act
    result = controller.save_portfolio(user_email, portfolio_data)

    # Assert
    assert portfolio_data in result

def test_portfolio_to_data():
    pass