import os

import redis
from dotenv import load_dotenv


load_dotenv()


def get_redis_client() -> redis.Redis:
    """创建 Redis 客户端，优先支持云平台 REDIS_URL，并兼容本地 .env 配置。"""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.Redis.from_url(redis_url, decode_responses=True)

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))

    return redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=True,
    )


redis_client = get_redis_client()