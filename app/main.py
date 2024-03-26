import os
import tempfile
from datetime import datetime

import redis
from fastapi import FastAPI, Response, Depends
from fastapi.responses import JSONResponse

from app.functions import do_download, load_csv_file

app = FastAPI()


async def get_redis_connection():
    try:
        connection = redis.Redis(
            host=os.environ["REDIS_HOST"],
            port=os.environ["REDIS_PORT"],
            decode_responses=True,
        )
        yield connection
    finally:
        connection.close()


@app.get("/search")
async def search(domain: str,
                 prefixSearch=None,
                 redis=Depends(get_redis_connection)):
    val = list(redis.smembers(f"domain:{domain}"))
    return JSONResponse(status_code=200, content={"urls": val})


@app.get("/download")
async def download(
    download_from: datetime,
    response: Response,
    download_to: datetime = None,
    test_data=None,
    redis=Depends(get_redis_connection)
):
    url = os.environ["PHISHTANK_URL"]

    with tempfile.NamedTemporaryFile() as temporary_file:

        if test_data:
            # don't download data, load it from local storage
            downloadSuccesfull = True
            temporary_file = "/code/offline_data/verified_online_small.csv"
        else:
            temporary_file = temporary_file.name
            downloadSuccesfull = await do_download(url,
                                                   temporary_file,
                                                   response)

        if not downloadSuccesfull:
            return JSONResponse(
                status_code=500,
                content={"message": "Download failed"}
            )
        else:
            return load_csv_file(temporary_file,
                                 redis,
                                 download_from,
                                 download_to
                                 )
