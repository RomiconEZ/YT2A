from beanie import Document, PydanticObjectId

from app.core.video import model

class Video(Document, model.Video):
    ...


class VideoStore(Video):
    """Store class for Youtube video."""

    async def create(video_id: str) -> model.Video | Exception:
        try:
            document = Video(youtube_id=video_id)
            
            await document.create()

            return model.Video(
                uid=str(document.id),
                **document.dict(exclude={"id"}),
            )

        except Exception() as exc:
            return exc
        
    async def get_by_id(video_id: str) -> model.Video:
        document = await Video.find(
            Video.uid == PydanticObjectId(video_id)
        ).first_or_none()

        if document is None:
            return None
        
        return model.Video(
                uid=str(document.id),
                **document.dict(exclude={"id"}),
        ) 

__video_store = None

def get_video_store() -> VideoStore:
    
    if __video_store is None:
        __video_store = VideoStore()

    return __video_store

