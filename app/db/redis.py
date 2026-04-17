"""
Conexión async a Redis.
Provee el cliente Redis compartido para caché de sesiones y tokens revocados.
"""

from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Devuelve el cliente Redis singleton (conexión lazy)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def save_refresh_token(user_id: str, token_hash: str, ttl_days: int) -> None:
    """
    Guarda un refresh token hasheado en Redis con TTL.
    También mantiene un set de tokens por usuario para logout-all.
    """
    client = await get_redis()
    ttl_seconds = ttl_days * 86_400

    pipe = client.pipeline()
    pipe.setex(f"refresh:{token_hash}", ttl_seconds, user_id)
    pipe.sadd(f"user_tokens:{user_id}", token_hash)
    pipe.expire(f"user_tokens:{user_id}", ttl_seconds)
    await pipe.execute()


async def get_refresh_token(token_hash: str) -> Optional[str]:
    """
    Devuelve el user_id asociado al token_hash, o None si no existe / expiró.
    """
    client = await get_redis()
    return await client.get(f"refresh:{token_hash}")


async def delete_refresh_token(token_hash: str) -> None:
    """Elimina un refresh token de Redis y lo quita del set del usuario."""
    client = await get_redis()
    user_id = await client.get(f"refresh:{token_hash}")

    pipe = client.pipeline()
    pipe.delete(f"refresh:{token_hash}")
    if user_id:
        pipe.srem(f"user_tokens:{user_id}", token_hash)
    await pipe.execute()


async def delete_all_user_tokens(user_id: str) -> None:
    """Elimina todos los refresh tokens de un usuario (logout en todos los dispositivos)."""
    client = await get_redis()
    token_hashes = await client.smembers(f"user_tokens:{user_id}")

    pipe = client.pipeline()
    for token_hash in token_hashes:
        pipe.delete(f"refresh:{token_hash}")
    pipe.delete(f"user_tokens:{user_id}")
    await pipe.execute()


async def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> bool:
    """
    Verifica el rate limit para una clave dada usando contador en Redis.
    Devuelve True si el request está permitido, False si excedió el límite.
    """
    client = await get_redis()
    redis_key = f"rate:{key}"

    count = await client.incr(redis_key)
    if count == 1:
        # Primera petición en esta ventana — establecer TTL
        await client.expire(redis_key, window_seconds)

    return count <= max_attempts
