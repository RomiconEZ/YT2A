import fastapi
import fpdf
import pydantic
from urllib.parse import urlparse, parse_qs

from app.core.timestamp.service import get_timestamp_service
from app.core.timestamp.model import TimestampInfo
from app.api import contract

router = fastapi.APIRouter(prefix="/video")

@router.get("/pdf")
async def get_pdf(
    url: pydantic.HttpUrl
):
    url_data = urlparse(url)
    query = parse_qs(url_data.query)
    video_id = query["v"][0]

    match await get_timestamp_service().get_by_video_id(video_id):
        case Exception() as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )
        case list() as timestamps:
            # timestamps to pdf
            pdf = fpdf.FPDF()
            pdf.add_page()
            pdf.set_font('Times', '', 12)
            for ts in timestamps:
                pdf.cell(0, 10, f'{ts.start_time}:{ts.end_time}\n' + ts.description)
            return fastapi.Response(content=pdf, media_type='application/pdf')

@router.get("/timestamps")
async def get_timestamps(
    url: pydantic.HttpUrl
):
    url_data = urlparse(url)
    query = parse_qs(url_data.query)
    video_id = query["v"][0]

    match await get_timestamp_service().get_by_video_id(video_id):
        case Exception() as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )
        case list() as timestamps:
            return contract.Timestamps(count=len(timestamps), timestamps=timestamps)
        
@router.get("/timestamp_info")
async def get_timestamp_info(
    url: pydantic.HttpUrl
):
    match await get_timestamp_service().get_by_video_id(url):
        case Exception() as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )
        case list() as timestamps:
            # timestamps to table

            return fastapi.Response(media_type='application/pdf')