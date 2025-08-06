import datetime
import json
import logging
from functools import wraps
from json import JSONDecodeError

from redis.asyncio import Redis

from configreader import config

redis = Redis(
    host=config.db_config.redis_host,
    port=config.db_config.redis_port,
    db=config.db_config.redis_db,
    password=config.db_config.redis_password if config.run_mode == "prod" else None,
    decode_responses=True,
)

logger = logging.getLogger(__name__)


def _make_cache_key(func, args, kwargs):
    # Формируем ключ только по простым типам (int, str, float)
    key_parts = [func.__name__]
    for arg in args:
        if isinstance(arg, (int, str, float)):
            key_parts.append(str(arg))
        elif isinstance(arg, (datetime.datetime, datetime.date)):
            key_parts.append(arg.isoformat())
        else:
            key_parts.append(str(type(arg)))
    for k, v in kwargs.items():
        if isinstance(v, (int, str, float)):
            key_parts.append(f"{k}={v}")
        elif isinstance(v, (datetime.datetime, datetime.date)):
            key_parts.append(f"{k}={v.isoformat()}")
        else:
            key_parts.append(f"{k}={type(v)}")
    return ":".join(key_parts)


def json_serializer(obj):
    """Кастомный сериализатор для JSON"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    # Для других неподдерживаемых типов
    return str(obj)


def redis_cache(expiration=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = _make_cache_key(func, args, kwargs)
            if kwargs.get("update_cache", False):
                logger.info("Force cache update for key: %s", key)
                result = await func(*args, **kwargs)
                try:
                    value_json = json.dumps(result, default=json_serializer)
                except Exception as e:
                    logger.info(f"Failed to serialize result: {e}")
                    value_json = str(result)
                await redis.set(key, value_json, ex=expiration)
                return result
            cached_result = await redis.get(key)
            if cached_result:
                value_json = cached_result
                try:
                    value = json.loads(value_json)
                    return value
                except JSONDecodeError as e:
                    logger.info(f"Failed to load cached result: {e}")
                    await redis.delete(key)  # Удаляем повреждённый кэш

            result = await func(*args, **kwargs)
            try:
                value_json = json.dumps(result, default=json_serializer)
                await redis.set(key, value_json, ex=expiration)
            except Exception as e:
                logger.info(f"Failed to serialize result: {e}")
            return result

        return wrapper

    return decorator


async def get_user_locale(user_id: int):
    user_locale = await redis.get(f"user:{user_id}:locale")
    if user_locale:
        return user_locale
    return None


async def set_user_locale(user_id: int, locale: str):
    await redis.set(f"user:{user_id}:locale", locale)

