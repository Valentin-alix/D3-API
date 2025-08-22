import logging
import os
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from time import sleep

import uvicorn
from dotenv import get_key
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

sys.path.append(os.path.join(Path(__file__).parent, "D3Database"))

from src.const import ENV_PATH
from src.routers import item_price_history, data_center, character


@asynccontextmanager
async def lifespan(app: FastAPI):
    while not is_db_ready(get_key(ENV_PATH, "DB_HOST") or "localhost", 5432):
        print("waiting for reachable db")
        sleep(1)
    os.system(
        f"poetry run alembic --config {os.path.join(Path(__file__).parent, 'src', 'alembic', 'alembic.ini')} upgrade head"
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: StarletteHTTPException):
    # the client sent invalid datas
    return PlainTextResponse(str(exc), status_code=400)


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)

logger.info("API is starting.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(item_price_history.router)
app.include_router(data_center.router)
app.include_router(character.router)


def is_db_ready(host: str, port: int) -> bool:
    """Vérifie si la base de données est prête pour les connexions."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    os.system(
        f"docker-compose -f {os.path.join(Path(__file__).parent, 'docker-compose.dev.yml')} up -d"
    )
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
