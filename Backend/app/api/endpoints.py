import fastapi
import pydantic

router = fastapi.APIRouter(prefix="/video")

@router.get("/pdf")
async def get_pdf(
    url: pydantic.HttpUrl
):
    pass

@router.get("/table")
async def get_table(
    url: pydantic.HttpUrl
):
    pass