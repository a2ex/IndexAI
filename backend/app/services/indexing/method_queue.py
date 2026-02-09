import json
import logging
import time
from redis import Redis
from app.config import settings

logger = logging.getLogger(__name__)

# Method priority: delay in seconds from submission time
METHOD_PRIORITY = {
    "indexnow": 0,
    "pingomatic": 120,       # +2 min
    "websub": 240,            # +4 min
    "archive_org": 480,       # +8 min
    "backlink_pings": 720,    # +12 min
    "google_api": 1800,       # +30 min
}

# Rate limits: (max_calls, window_seconds)
RATE_LIMITS = {
    "indexnow": (100, 60),
    "pingomatic": (30, 60),
    "websub": (30, 60),
    "archive_org": (15, 60),
    "backlink_pings": (30, 60),
    "google_api": None,  # managed by ServiceAccountManager
}

MAX_RETRIES = 3
BACKOFF_BASE = 300  # 5 minutes

QUEUE_KEY = "mq:queue"
RATE_KEY_PREFIX = "mq:rate:"
LOCK_KEY_PREFIX = "mq:lock:"

# Lua script for atomic pop of eligible jobs
_POP_ELIGIBLE_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local batch = tonumber(ARGV[2])
local results = redis.call('ZRANGEBYSCORE', key, '-inf', now, 'LIMIT', 0, batch)
if #results > 0 then
    redis.call('ZREM', key, unpack(results))
end
return results
"""


def _get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def enqueue_url_methods(url_id: str, project_id: str, indexnow_config: dict | None = None):
    """Push 6 jobs into the Redis sorted set with staggered scores."""
    r = _get_redis()
    now = time.time()
    mapping = {}

    for method, delay in METHOD_PRIORITY.items():
        job = json.dumps({
            "url_id": url_id,
            "project_id": project_id,
            "method": method,
            "attempt": 0,
            "indexnow_config": indexnow_config,
        })
        mapping[job] = now + delay

    r.zadd(QUEUE_KEY, mapping)
    logger.info(f"Enqueued {len(mapping)} jobs for url_id={url_id}")


def pop_eligible_jobs(batch_size: int = 50) -> list[dict]:
    """Atomically pop jobs whose score <= now using a Lua script."""
    r = _get_redis()
    now = time.time()
    raw_jobs = r.eval(_POP_ELIGIBLE_LUA, 1, QUEUE_KEY, now, batch_size)
    jobs = []
    for raw in raw_jobs:
        try:
            jobs.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Skipping malformed job: {raw}")
    return jobs


def check_rate_limit(method: str) -> bool:
    """Return True if the method is within its rate limit, False if exceeded."""
    limit_config = RATE_LIMITS.get(method)
    if limit_config is None:
        return True  # no rate limit (e.g. google_api managed externally)

    max_calls, window = limit_config
    r = _get_redis()
    key = f"{RATE_KEY_PREFIX}{method}"

    current = r.incr(key)
    if current == 1:
        r.expire(key, window)

    if current > max_calls:
        return False
    return True


def acquire_url_lock(url_id: str, ttl: int = 120) -> bool:
    """Try to acquire a lock for a URL. Returns True if acquired."""
    r = _get_redis()
    key = f"{LOCK_KEY_PREFIX}{url_id}"
    return bool(r.set(key, "1", nx=True, ex=ttl))


def release_url_lock(url_id: str):
    """Release the lock for a URL."""
    r = _get_redis()
    key = f"{LOCK_KEY_PREFIX}{url_id}"
    r.delete(key)


def requeue_job(job: dict, delay: float):
    """Put a job back into the queue with a future score."""
    r = _get_redis()
    score = time.time() + delay
    raw = json.dumps(job)
    r.zadd(QUEUE_KEY, {raw: score})
    logger.info(
        f"Requeued {job['method']} for url_id={job['url_id']} "
        f"(attempt {job['attempt']}, delay {delay}s)"
    )


def get_queue_stats() -> dict:
    """Return monitoring stats about the queue."""
    r = _get_redis()
    now = time.time()
    total = r.zcard(QUEUE_KEY)
    eligible = r.zcount(QUEUE_KEY, "-inf", now)
    delayed = r.zcount(QUEUE_KEY, now, "+inf")
    return {"total": total, "eligible": eligible, "delayed": delayed}
