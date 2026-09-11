"""Her profile: nickname, avatar, colour theme.

Deliberately separate from anything Cognito holds. The account (email, PIN)
exists so a parent can set it up and keep it recoverable; the profile is
hers to choose and change freely, so the app feels like something she owns
rather than a portal her parent set up for her.
"""

from __future__ import annotations

from dataclasses import dataclass

_MAX_NICKNAME_LENGTH = 20
_ALLOWED_AVATARS = frozenset({"fox", "owl", "otter", "comet", "cactus", "wave"})
_ALLOWED_COLOUR_THEMES = frozenset({"indigo", "coral", "teal", "amber", "violet"})


class ProfileValidationError(ValueError):
    """Raised when a submitted profile update fails validation."""


@dataclass(frozen=True)
class Profile:
    user_id: str
    nickname: str
    avatar: str
    colour_theme: str


def validate_profile_update(*, nickname: str, avatar: str, colour_theme: str) -> None:
    """Raise ProfileValidationError if any field is unusable; otherwise return."""
    nickname = nickname.strip()
    if not nickname:
        raise ProfileValidationError("Nickname can't be empty.")
    if len(nickname) > _MAX_NICKNAME_LENGTH:
        raise ProfileValidationError(f"Nickname must be {_MAX_NICKNAME_LENGTH} characters or fewer.")
    if avatar not in _ALLOWED_AVATARS:
        raise ProfileValidationError(f"Unknown avatar '{avatar}'.")
    if colour_theme not in _ALLOWED_COLOUR_THEMES:
        raise ProfileValidationError(f"Unknown colour theme '{colour_theme}'.")


def build_profile(*, user_id: str, nickname: str, avatar: str, colour_theme: str) -> Profile:
    """Validate and construct a Profile, ready to persist."""
    validate_profile_update(nickname=nickname, avatar=avatar, colour_theme=colour_theme)
    return Profile(user_id=user_id, nickname=nickname.strip(), avatar=avatar, colour_theme=colour_theme)
