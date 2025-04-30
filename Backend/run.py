"""
Script to run the FastAPI application using the configuration system.
"""
import uvicorn
from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host=settings.api.host, 
        port=settings.api.port, 
        reload=settings.debug
    ) 