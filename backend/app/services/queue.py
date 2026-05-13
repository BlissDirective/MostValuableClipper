import json
from typing import Optional, Any, Dict, List
import redis
from upstash_redis import Redis
from app.core.config import settings

class QueueService:
    """Job queue service using Upstash Redis."""
    
    def __init__(self):
        self.redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN
        )
    
    async def enqueue(
        self,
        queue_name: str,
        job_data: Dict[str, Any],
        delay_seconds: Optional[int] = None
    ) -> str:
        """Add a job to the queue."""
        job_json = json.dumps(job_data)
        
        if delay_seconds:
            # Schedule for later using sorted set
            score = delay_seconds
            self.redis.zadd(f"delayed:{queue_name}", {job_json: score})
        else:
            # Add to queue immediately
            self.redis.lpush(f"queue:{queue_name}", job_json)
        
        return job_data.get("job_id", "")
    
    async def dequeue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Get the next job from the queue."""
        result = self.redis.brpop(f"queue:{queue_name}", timeout=1)
        if result:
            return json.loads(result[1])
        return None
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Get the number of jobs in the queue."""
        return self.redis.llen(f"queue:{queue_name}")
    
    async def mark_job_complete(self, job_id: str, result: Dict[str, Any]):
        """Mark a job as completed."""
        self.redis.setex(f"job:{job_id}:result", 86400, json.dumps(result))
        self.redis.setex(f"job:{job_id}:status", 86400, "completed")
    
    async def mark_job_failed(self, job_id: str, error: str):
        """Mark a job as failed."""
        self.redis.setex(f"job:{job_id}:status", 86400, "failed")
        self.redis.setex(f"job:{job_id}:error", 86400, error)
    
    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Get the status of a job."""
        status = self.redis.get(f"job:{job_id}:status")
        return status

class CacheService:
    """Simple caching service using Upstash Redis."""
    
    def __init__(self):
        self.redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        value = self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300
    ):
        """Set a cached value with TTL."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.redis.setex(key, ttl_seconds, value)
    
    async def delete(self, key: str):
        """Delete a cached value."""
        self.redis.delete(key)
    
    async def get_or_set(
        self,
        key: str,
        factory,
        ttl_seconds: int = 300
    ) -> Any:
        """Get from cache or set using factory function."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        value = await factory()
        await self.set(key, value, ttl_seconds)
        return value
