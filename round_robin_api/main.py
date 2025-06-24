from fastapi import FastAPI, Request
import aiohttp
import asyncio
import socket
import logging
import os
import redis.asyncio as redis
import uuid

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger()

app = FastAPI()
REFRESH_INTERVAL = 5


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
POD_ID = os.getenv("HOSTNAME", "")
ROUND_ROBIN_KEY = f"rr:index:{POD_ID}"
logger.info(f"ROUND_ROBIN_KEY: {ROUND_ROBIN_KEY}")

app_servers = []
session: aiohttp.ClientSession = None
redis_client: redis.Redis = None


async def discover_app_servers():
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo("app-api", 5000, proto=socket.IPPROTO_TCP)
        ips = sorted(set(info[4][0] for info in infos))
        logger.info(f"Discovered app-api pods: {ips}")
        return [f"http://{ip}:5000/payload" for ip in ips]
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return []

async def periodic_discovery():
    global app_servers
    logger.info("🟢 Starting background discovery task")
    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        try:
            new_servers = await discover_app_servers()
            if sorted(new_servers) != sorted(app_servers):
                app_servers[:] = new_servers
                logger.info("🔁 Refreshed app servers: %s", app_servers)
        except Exception as e:
            logger.error(f"❌ Periodic discovery failed: {e}")

async def init_redis_with_retry():
    global redis_client
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

    for attempt in range(10):
        try:
            await redis_client.setnx(ROUND_ROBIN_KEY, 0)
            logger.info(f"✅ Connected to Redis at {REDIS_HOST}")
            return
        except Exception as e:
            logger.warning(f"⏳ Waiting for Redis... (attempt {attempt+1}/10): {e}")
            await asyncio.sleep(2)
    raise RuntimeError("❌ Failed to connect to Redis after 10 attempts")

@app.on_event("startup")
async def startup_event():
    global app_servers, session
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1000))
    await init_redis_with_retry()
    app_servers[:] = await discover_app_servers()
    asyncio.create_task(periodic_discovery())

@app.on_event("shutdown")
async def shutdown_event():
    await session.close()
    await redis_client.close()

@app.post("/route")
async def route(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request: {repr(e)}")
        return {"error": "Invalid JSON"}, 400

    num_servers = len(app_servers)
    if num_servers == 0:
        return {"error": "No backend servers available"}, 503

    for _ in range(num_servers):
        try:
            index = await redis_client.incr(ROUND_ROBIN_KEY)
            index = (index - 1) % num_servers
            target = app_servers[index]
            logger.info(f"Routing to: {target} [index={index}]")

            async with session.post(target, json=data, timeout=aiohttp.ClientTimeout(total=1.5)) as resp:
                return await resp.json()

        except Exception as e:
            logger.error(f"Error calling backend [{target}]: {repr(e)}")
            continue
    return {"error": "All backend servers failed"}, 503