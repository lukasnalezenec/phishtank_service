import csv
import logging
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

import aiofile
import aiohttp
from fastapi import Response
from fastapi.responses import JSONResponse

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


def extractTLD(domain):
    """  Extracts TLD from given domain """
    loc = domain.rfind(".")
    if loc == -1 or loc == len(domain):
        return None
    else:
        return domain[loc + 1:]


def write_to_redis(batch, redis):
    """ Writes given list of records in batch to Redis """

    if len(batch) != 0:
        try:
            pipe = redis.pipeline()
            for record in batch:
                redis_key = "domain:" + urlparse(record[0]).netloc
                pipe.sadd(redis_key, record[1])
        finally:
            pipe.execute()
            redis.close()
            batch.clear()


async def do_download(url, filepath, response: Response):
    """ Downloads given url to file """

    logger.info(f"Downloading {url=} to {filepath=}")

    DEFAULT_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 \
                     (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"

    async with aiohttp.ClientSession(
            headers={"User-Agent:": DEFAULT_AGENT}) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()

                async with aiofile.async_open(filepath, "wb") as outfile:
                    await outfile.write(data)
                    logger.info(
                        f"Download successfull - \
                        {resp.status=} \
                        {resp.headers.get('last-modified', '')=} \
                        {resp.headers.get('Content-Length', '')=}"
                    )
                    return True
            else:
                logger.warning(
                    f"Download failed: \
                    {resp.status}\n{resp}"
                )
                return False


def load_csv_file(file,
                  redis,
                  from_time: datetime,
                  to_time: datetime = None,
                  batch_size=100):
    """ Loads data from local CSV file to Redis"""
    logger.info(f"Parsing file {file=} {from_time=} {to_time=}")
    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)

        tld_counter = Counter()
        urls = []
        errors = []
        batch = []

        for row in reader:
            try:
                submission_time = datetime.fromisoformat(
                    row["submission_time"])
                in_interval = submission_time >= from_time or (
                    (not to_time) or submission_time <= to_time
                )
                if in_interval:
                    phish_id = row["phish_id"]
                    url = row["url"]
                    detail_url = row["phish_detail_url"]

                    domain = urlparse(url).netloc
                    tld = extractTLD(domain)

                    tld_counter[tld] += 1
                    urls.append(url)

                    redisRecord = (url, phish_id, detail_url)
                    batch.append(redisRecord)
                    if len(batch) >= batch_size:
                        write_to_redis(batch, redis)

            except Exception as e:
                logger.error(
                    "Unable to process CSV line \n' %s '\n \
                    with column names \n%s"
                    % (row, reader.fieldnames),
                    e,
                )
                errors.append(url)

        write_to_redis(batch, redis)

        if len(errors) > 0:
            return JSONResponse(
                status_code=500,
                content={"message": "Unable to load file. See logs"}
            )
        else:
            logger.info(f"{len(urls)} records written to Redis.")
            return JSONResponse(
                status_code=200,
                content={
                    "urls": urls,
                    "top_tlds": tld_counter.most_common(),
                    "count": len(urls),
                },
            )
