import pydantic

from app.core.timestamp import model

class Timestamps(pydantic.BaseModel):

    count: int
    timestamps: list[model.TimestampInfo]