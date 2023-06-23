from app.core.timestamp import model
from app.core.video.service import get_video_service
from app.service.timestamp import get_timestamp_store

class Service:

    async def get_by_video_id(
        video_id: str
    ) -> list[model.TimestampInfo] | Exception:
        video = await get_video_service().get_by_id(video_id)

        if video is None:
            try:
                video = await get_video_service().create(video_id)


                # timestamps = timestamps_by_video_id
                # 
                #     
            except Exception() as exc:
                return exc

        return await get_timestamp_store().get_by_video_uid(video.uid)


__timestamp_service = None

def get_timestamp_service() -> Service:

    if __timestamp_service is None:
        __timestamp_service = Service()
    
    return __timestamp_service