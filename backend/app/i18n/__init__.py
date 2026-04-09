"""
Internationalization module for MiroFish backend.
Provides localized prompts and API messages.
"""

from ..config import Config


def get_locale():
    """Return the current locale (read fresh from Config each time)."""
    return Config.APP_LOCALE


def get_prompt(key: str) -> str:
    """Get a localized LLM prompt by key."""
    locale = Config.APP_LOCALE
    if locale == 'it':
        from .prompts import it as prompts_mod
    elif locale == 'en':
        from .prompts import en as prompts_mod
    else:
        from .prompts import zh as prompts_mod
    return getattr(prompts_mod, key)


def get_message(key: str, **kwargs) -> str:
    """Get a localized API response message, with optional formatting."""
    locale = Config.APP_LOCALE
    if locale == 'it':
        from .messages import it as msg_mod
    elif locale == 'en':
        from .messages import en as msg_mod
    else:
        from .messages import zh as msg_mod
    template = getattr(msg_mod, key)
    return template.format(**kwargs) if kwargs else template
