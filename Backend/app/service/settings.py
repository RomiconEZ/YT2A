from typing import Any, Mapping

from pydantic import BaseSettings, Field, SecretStr, validator


class MongoSettings(BaseSettings):  # noqa
    USERNAME: str = Field(default="yt2a-user")
    PASSWORD: SecretStr = Field(default="yt2a-user-password")
    HOST: str = Field(default="localhost")
    PORT: int = Field(default=27017)
    DATABASE: str = Field(default="yt2a")

    CONNECTION_STR: str = Field(default="")

    @validator("CONNECTION_STR", pre=True)
    def _compose_connection_str(
        cls,  # noqa
        v: str | None,
        values: Mapping[str, Any],
    ) -> str:
        if v and isinstance(v, str):
            return v

        username: str = values["USERNAME"]
        secret_password: SecretStr = values["PASSWORD"]
        host: str = values["HOST"]
        port: int = values["PORT"]
        password: str = secret_password.get_secret_value()

        return f"mongodb://{username}:{password}@{host}:{port}"

    class Config:  # noqa
        env_prefix = "MONGODB_"
        frozen = True

__database_settings = None

def get_database_settings() -> MongoSettings: 
    """
    Get database settings.

    Returns:
        MongoSettings: database settings   
    """

    if __database_settings is None:
        __database_settings = MongoSettings()

    return __database_settings