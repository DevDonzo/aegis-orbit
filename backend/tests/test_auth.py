from core.auth import authenticate_user, create_access_token, decode_access_token, get_user_registry, verify_password
from core.config import settings


def test_bootstrap_user_is_available() -> None:
    users = get_user_registry()
    assert settings.demo_username in users
    assert verify_password(settings.demo_password, users[settings.demo_username].password_hash)


def test_can_issue_and_decode_jwt() -> None:
    user = authenticate_user(settings.demo_username, settings.demo_password)
    assert user is not None
    token = create_access_token(user)
    claims = decode_access_token(token)
    assert claims.sub == settings.demo_username
    assert claims.role == settings.demo_role
