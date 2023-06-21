import enum

import pydantic


class Environment(enum.Enum):
    """Possible environments of app."""

    DEBUG = "DEBUG"  # local debug
    DOCKER = "DOCKER"  # local testing with docker
    PRODUCTION = "PRODUCTION"  # production or production-like environment

class App(pydantic.BaseSettings):
    """General application config."""

    TITLE: str = pydantic.Field(default="Youtube2Article")
    VERSION: str = pydantic.Field(default="0.0.1")
    ENVIRONMENT: Environment = pydantic.Field()

    class Config:  # noqa
        env_prefix = "BE_APP_"
        frozen = True

__settings = None

def get_settings() -> App: 
    """
    Get app settings.

    Returns:
        App: app settings   
    """

    if __settings is None:
        __settings = App()

    return __settings