from app.core.video import model
from app.service.video import get_video_store

class Service:

    async def create(video_id: str) -> model.Video:
        try:
            return get_video_store().create(video_id)
        except Exception() as exc:
            return exc


    async def get_by_id(video_id: str) -> model.Video:
        return get_video_store().get_by_id(video_id)

__video_service = None

def get_video_service() -> Service:

    if __video_service is None:
        __video_service = Service()
    
    return __video_service