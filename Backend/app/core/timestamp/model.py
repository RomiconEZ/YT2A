import pydantic

from datetime import time
from typing import Optional


class TimestampInfo(pydantic.BaseModel):
    """Timestamp model without description."""

    uid: str 

    start_time: time
    end_time: time


class Timestamp(TimestampInfo):
    """Timestamp model."""

    description: str
    video_uid: str