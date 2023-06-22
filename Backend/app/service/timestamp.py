from beanie import Document, PydanticObjectId
from datetime import time

from app.core.timestamp import model

class Timestamp(Document, model.Timestamp):
    ...

class TimestampStore():
    """Class for timestamp of a video."""

    async def get_by_video_uid(
            video_uid: str,
    ) -> list[model.TimestampInfo]:
        document = await Timestamp.find(
            Timestamp.video_uid == PydanticObjectId(video_uid)
        ).to_list()

        if document is None:
            return []
        
        return [
            model.TimestampInfo(
                uid=str(ts.id),
                start_time=ts.start_time,
                end_time=ts.end_time
            ) for ts in document
        ]

    async def get_by_uid(
            uid: str,    
    ) -> model.Timestamp | None:

        document = await Timestamp.find(
            Timestamp.uid == PydanticObjectId(uid)
        ).first_or_none()

        if document is None:
            return None
        
        return model.Timestamp(
                uid=str(document.id),
                **document.dict(exclude={"id"}),
        ) 
    
__timestamp_store = None

def get_timestamp_store() -> TimestampStore:
    
    if __timestamp_store is None:
        __timestamp_store = TimestampStore()

    return __timestamp_store
