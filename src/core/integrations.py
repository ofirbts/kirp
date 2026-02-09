"""
Integration Layer — Unified clients for all services.

MongoDB, Redis, PostgreSQL, Cassandra, Kafka, Elasticsearch.
Provider-agnostic; supports local + Bootcamp configs.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


# === MongoDB ===
_mongo_clients: dict[str, Any] = {}  # Connection pooling

@lru_cache
def get_mongo_client(use_bootcamp: bool = False):
    """Get MongoDB client with connection pooling. Cached singleton."""
    cache_key = "bootcamp" if use_bootcamp else "default"
    if cache_key in _mongo_clients:
        return _mongo_clients[cache_key]
    
    uri = os.getenv("BOOTCAMP_MONGO_URI" if use_bootcamp else "MONGO_URI", "")
    if not uri:
        raise ValueError("MONGO_URI not set")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        # Connection pooling via maxPoolSize
        client = AsyncIOMotorClient(uri, maxPoolSize=50, minPoolSize=5)
        _mongo_clients[cache_key] = client
        return client
    except ImportError:
        from pymongo import MongoClient
        client = MongoClient(uri, maxPoolSize=50, minPoolSize=5)
        _mongo_clients[cache_key] = client
        return client


async def get_mongo_db(use_bootcamp: bool = False):
    """Get MongoDB database."""
    client = get_mongo_client(use_bootcamp)
    db_name = os.getenv("BOOTCAMP_MONGO_DB_NAME" if use_bootcamp else "MONGO_DB_NAME", "kirp")
    if hasattr(client, "get_database"):
        return client.get_database(db_name)
    return client[db_name]


# === Redis ===
@lru_cache
def get_redis_client(use_bootcamp: bool = False):
    """Get Redis client. Sync version."""
    if use_bootcamp:
        host = os.getenv("BOOTCAMP_REDIS_HOST", "node128.codingbc.com")
        port = int(os.getenv("BOOTCAMP_REDIS_PORT", "6000"))
    else:
        host = os.getenv("REDIS_HOST", "redis")
        port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        import redis
        return redis.Redis(host=host, port=port, decode_responses=True)
    except ImportError:
        logger.warning("redis not installed; returning None")
        return None


@lru_cache
def get_redis_async(use_bootcamp: bool = False):
    """Get async Redis client."""
    if use_bootcamp:
        url = f"redis://{os.getenv('BOOTCAMP_REDIS_HOST', 'node128.codingbc.com')}:{os.getenv('BOOTCAMP_REDIS_PORT', '6000')}/0"
    else:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        import redis.asyncio as redis
        return redis.from_url(url, decode_responses=True)
    except ImportError:
        logger.warning("redis.asyncio not installed")
        return None


# === PostgreSQL ===
_postgres_engines: dict[str, Any] = {}  # Connection pooling

@lru_cache
def get_postgres_engine(use_bootcamp: bool = False):
    """Get SQLAlchemy engine for PostgreSQL with connection pooling."""
    cache_key = "bootcamp" if use_bootcamp else "default"
    if cache_key in _postgres_engines:
        return _postgres_engines[cache_key]
    
    if use_bootcamp:
        host = os.getenv("BOOTCAMP_POSTGRES_HOST", "node128.codingbc.com")
        port = os.getenv("BOOTCAMP_POSTGRES_PORT", "7878")
        db = os.getenv("BOOTCAMP_POSTGRES_DB", "ofir_basidsprig")
        user = os.getenv("BOOTCAMP_POSTGRES_USER", "postgres")
        password = os.getenv("BOOTCAMP_POSTGRES_PASSWORD", "")
    else:
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "kirp")
        user = os.getenv("POSTGRES_USER", "kirp_user")
        password = os.getenv("POSTGRES_PASSWORD", "kirp_password")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    try:
        from sqlalchemy import create_engine
        # Connection pooling
        engine = create_engine(
            url,
            echo=False,
            future=True,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections
        )
        _postgres_engines[cache_key] = engine
        return engine
    except ImportError:
        logger.warning("sqlalchemy not installed")
        return None


def get_postgres_session(use_bootcamp: bool = False):
    """Get SQLAlchemy session."""
    engine = get_postgres_engine(use_bootcamp)
    if engine is None:
        return None
    try:
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        return Session()
    except Exception as e:
        logger.error("Failed to create postgres session: %s", e)
        return None


# === Cassandra ===
@lru_cache
def get_cassandra_session(use_bootcamp: bool = False):
    """Get Cassandra session. Creates keyspace if missing."""
    if use_bootcamp:
        host = os.getenv("BOOTCAMP_CASSANDRA_HOST", "node128.codingbc.com")
        port = int(os.getenv("BOOTCAMP_CASSANDRA_PORT", "9042"))
        keyspace = os.getenv("BOOTCAMP_CASSANDRA_KEYSPACE", "tiny_keyspace")
        dc = os.getenv("BOOTCAMP_CASSANDRA_DATACENTER", "datacenter1")
    else:
        host = os.getenv("CASSANDRA_HOST", "cassandra")
        port = int(os.getenv("CASSANDRA_PORT", "9042"))
        keyspace = os.getenv("CASSANDRA_KEYSPACE", "kirp_keyspace")
        dc = os.getenv("CASSANDRA_DATACENTER", "datacenter1")
    try:
        from cassandra.cluster import Cluster
        cluster = Cluster(contact_points=[host], port=port)
        session = cluster.connect()
        session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{ 'class': 'SimpleStrategy', 'replication_factor': 1 }};
            """
        )
        session.set_keyspace(keyspace)
        return session
    except ImportError:
        logger.warning("cassandra-driver not installed")
        return None
    except Exception as e:
        logger.error("Cassandra connection failed: %s", e)
        return None


# === Kafka ===
# Docker-internal hostname so producer and consumer connect to the same broker (avoids UNKNOWN_TOPIC_OR_PART).
KAFKA_BOOTSTRAP_DEFAULT = "kafka:9092"


def _kafka_bootstrap(use_bootcamp: bool = False) -> str:
    """Resolve Kafka bootstrap servers. Prefer Docker hostname kafka:9092 over localhost."""
    if use_bootcamp:
        return os.getenv("BOOTCAMP_KAFKA_BOOTSTRAP", "node128.codingbc.com:9092")
    raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP_DEFAULT)
    if raw in ("localhost:9092", "127.0.0.1:9092"):
        return KAFKA_BOOTSTRAP_DEFAULT
    return raw


@lru_cache
def get_kafka_producer(use_bootcamp: bool = False):
    """Get Kafka producer. Uses kafka:9092 by default (Docker hostname)."""
    bootstrap = _kafka_bootstrap(use_bootcamp)
    try:
        from confluent_kafka import Producer
        return Producer({"bootstrap.servers": bootstrap})
    except ImportError:
        logger.warning("confluent-kafka not installed")
        return None


def get_kafka_consumer(group_id: str, topics: list[str], use_bootcamp: bool = False, subscribe: bool = True):
    """Get Kafka consumer. Uses kafka:9092 by default (Docker hostname). If subscribe=False, caller must call consumer.subscribe() after topic is ready."""
    bootstrap = _kafka_bootstrap(use_bootcamp)
    try:
        from confluent_kafka import Consumer
        consumer = Consumer(
            {
                "bootstrap.servers": bootstrap,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
            }
        )
        if subscribe:
            consumer.subscribe(topics)
        return consumer
    except ImportError:
        logger.warning("confluent-kafka not installed")
        return None


# === Elasticsearch ===
@lru_cache
def get_elasticsearch_client(use_bootcamp: bool = False):
    """Get Elasticsearch client."""
    host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
    port = os.getenv("ELASTICSEARCH_PORT", "9200")
    try:
        from elasticsearch import Elasticsearch
        return Elasticsearch(f"http://{host}:{port}")
    except ImportError:
        logger.warning("elasticsearch not installed")
        return None
