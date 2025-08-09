import logging
import os
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from time import sleep

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

from src.routers import (
    character,
    collectable,
    config_user,
    equipment,
    item,
    job,
    line,
    login,
    map,
    price,
    recipe,
    server,
    spell,
    stat,
    sub_area,
    template,
    type_item,
    user,
    world,
    character_path_info,
    character_path_map,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(user.router)
app.include_router(character.router)
app.include_router(collectable.router)
app.include_router(item.router)
app.include_router(job.router)
app.include_router(map.router)
app.include_router(price.router)
app.include_router(recipe.router)
app.include_router(server.router)
app.include_router(spell.router)
app.include_router(sub_area.router)
app.include_router(type_item.router)
app.include_router(world.router)
app.include_router(template.router)
app.include_router(login.router)
app.include_router(config_user.router)
app.include_router(stat.router)
app.include_router(equipment.router)
app.include_router(line.router)
app.include_router(character_path_info.router)
app.include_router(character_path_map.router)


def is_db_ready(host: str, port: int) -> bool:
    """Vérifie si la base de données est prête pour les connexions."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    os.system(
        f"docker-compose -f {os.path.join(Path(__file__).parent, "docker-compose.dev.yml")} up -d"
    )
    while not is_db_ready("localhost", 5432):
        sleep(1)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
