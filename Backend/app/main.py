import fastapi
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as app_router
import config


__app = None

def get_app() -> fastapi.FastAPI:
    """
    Get FastAPI instance to run.

    Returns:
        FastAPI: app instance   
    """
    
    if __app is None:
        __app = fastapi.FastAPI(
            title=config.get_settings().TITLE,
            version=config.get_settings().VERSION,
        )
        
        __app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        __app.include_router(app_router)

    return __app
