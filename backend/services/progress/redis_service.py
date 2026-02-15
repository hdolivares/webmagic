"""
Redis Connection Service.

Purpose:
    Manage Redis connections for real-time progress publishing.
    Provides singleton pattern for connection pooling.

Best Practices:
    - Singleton pattern prevents connection sprawl
    - Lazy initialization
    - Graceful degradation if Redis unavailable
    - Connection pooling for performance
"""

import logging
from typing import Optional
from redis import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError

from core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis connection manager (Singleton).
    
    Provides a single Redis connection pool shared across the application.
    Falls back gracefully if Redis is unavailable.
    
    Usage:
        redis = RedisService.get_client()
        redis.publish("channel", "message")
    """
    
    _instance: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None
    _is_available: bool = False
    
    @classmethod
    def get_client(cls) -> Redis:
        """
        Get Redis client instance (singleton).
        
        Returns:
            Connected Redis client or DummyRedis if unavailable
        """
        if cls._instance is None:
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        """
        Initialize Redis connection pool and client.
        
        Attempts to connect to Redis. If connection fails, creates
        a dummy client that logs warnings instead of crashing.
        """
        try:
            # Create connection pool
            cls._pool = ConnectionPool(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,  # Return strings not bytes
                max_connections=20,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Create client from pool
            cls._instance = Redis(connection_pool=cls._pool)
            
            # Test connection
            cls._instance.ping()
            cls._is_available = True
            
            logger.info("✅ Redis connection established successfully")
            logger.info(f"   Host: {getattr(settings, 'REDIS_HOST', 'localhost')}")
            logger.info(f"   Port: {getattr(settings, 'REDIS_PORT', 6379)}")
            
        except (ConnectionError, TimeoutError, AttributeError) as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            logger.warning("   Progress updates will be disabled (graceful degradation)")
            
            # Create dummy client that doesn't crash
            cls._instance = _DummyRedis()
            cls._is_available = False
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if Redis is available.
        
        Returns:
            True if connected, False if using dummy client
        """
        return cls._is_available
    
    @classmethod
    def close(cls):
        """
        Close Redis connection and cleanup.
        
        Should be called on application shutdown.
        """
        if cls._instance and cls._is_available:
            try:
                cls._instance.close()
                logger.info("📴 Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")
        
        if cls._pool:
            try:
                cls._pool.disconnect()
            except Exception:
                pass
        
        cls._instance = None
        cls._pool = None
        cls._is_available = False


class _DummyRedis:
    """
    Dummy Redis client for graceful degradation.
    
    When Redis is unavailable, this class prevents crashes by
    logging warnings instead of raising exceptions.
    
    All methods return None and log a warning.
    """
    
    def __getattr__(self, name):
        """
        Intercept all method calls and return a no-op function.
        
        Args:
            name: Method name being called
            
        Returns:
            Function that logs warning and returns None
        """
        def no_op_method(*args, **kwargs):
            logger.debug(f"Redis unavailable: skipping {name}()")
            return None
        
        return no_op_method
    
    def ping(self):
        """Override ping to return False."""
        return False
