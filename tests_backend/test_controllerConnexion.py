import pytest
from unittest.mock import Mock, AsyncMock
from authentification.controllerConnexion import controllerConnexion


login = Mock()


# get_auth_url
login.get_auth_url.return_value = "fake_auth_url"

# handle_callback
login.handle_callback = AsyncMock(return_value=(
    {"id": 1, "google_id": "google_123", "email": "test@gmail.com", "user_name": "Test User", "admin": False},
    None
))

# create_jwt
login.create_jwt.return_value = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.token"

# verify_jwt
login.verify_jwt.return_value = (
    {"email": "test@gmail.com", "username": "Test User", "admin": False},
    None  # pas d'erreur
)


controller = controllerConnexion(login=login)

def test_get_auth_url():
    response = controller.get_auth_url()
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_handle_callback():
    user, error = await controller.handle_callback("fake_code")
    assert error is None
    assert user["email"] == "test@gmail.com"


@pytest.mark.asyncio
async def test_handle_callback_failure():
    controller.serviceLogin.handle_callback = AsyncMock(return_value=(None, "Failed to get access token"))
    user, error = await controller.handle_callback("bad_code")
    assert user is None
    assert error == "Failed to get access token"


def test_create_jwt():
    user = {"email": "test@gmail.com", "user_name": "Test User", "admin": False}
    token = controller.create_jwt(user)
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_jwt():
    payload, error = controller.verify_jwt("fake.jwt.token")
    assert error is None
    assert payload["email"] == "test@gmail.com"


def test_verify_jwt_expired():
    controller.serviceLogin.verify_jwt.return_value = (None, "Token expiré")
    payload, error = controller.verify_jwt("expired.token")
    assert payload is None
    assert error == "Token expiré"


def test_verify_jwt_invalid():
    controller.serviceLogin.verify_jwt.return_value = (None, "Token invalide")
    payload, error = controller.verify_jwt("invalid.token")
    assert payload is None
    assert error == "Token invalide"

