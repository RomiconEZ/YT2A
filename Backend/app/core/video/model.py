import pydantic
from typing import Optional


class Video(pydantic.BaseModel):
    """Video model."""

    uid: str 
    youtube_id: str