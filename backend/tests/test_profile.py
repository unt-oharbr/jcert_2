import pytest

from axiom.profile import ProfileValidationError, build_profile, validate_profile_update


def test_build_profile_happy_path():
    profile = build_profile(user_id="abc123", nickname="  Nova  ", avatar="fox", colour_theme="teal")
    assert profile.nickname == "Nova"  # trimmed
    assert profile.avatar == "fox"
    assert profile.colour_theme == "teal"
    assert profile.user_id == "abc123"


def test_empty_nickname_is_rejected():
    with pytest.raises(ProfileValidationError):
        validate_profile_update(nickname="   ", avatar="fox", colour_theme="teal")


def test_overlong_nickname_is_rejected():
    with pytest.raises(ProfileValidationError):
        validate_profile_update(nickname="x" * 21, avatar="fox", colour_theme="teal")


def test_unknown_avatar_is_rejected():
    with pytest.raises(ProfileValidationError):
        validate_profile_update(nickname="Nova", avatar="dragon", colour_theme="teal")


def test_unknown_colour_theme_is_rejected():
    with pytest.raises(ProfileValidationError):
        validate_profile_update(nickname="Nova", avatar="fox", colour_theme="beige")
