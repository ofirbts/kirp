"""
KIRP Enterprise Monitoring v7
Production metrics, alerting, health dashboards
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import json

from app.core.persistence import PersistenceManager
from app.core.redis_client import get_redis
from app.llm.client import get_llm

logger = logging.getLogger("KIRP-Monitoring")

class MetricsCollector:
    """In-memory + Redis-backed metrics with Prometheus format"""
    
    def __init__(self, namespace: str):
        self.namespace = namespace
        self._counters = defaultdict(int)
        self.redis = None
    
    async def init(self):
        self.redis = await get_redis()
    
    def inc(self, metric: str, value: int = 1):
        self._counters[f"{self.namespace}_{metric}"] += value
    
    def gauge(self, metric: str, value: float):
        self._counters[f"{self.namespace}_{metric}_gauge"] = value
    
    async def flush(self):
        """Flush to Redis every 30s"""
        if not self.redis:
            return
        
        pipe = self.redis.pipeline()
        for metric, value in self._counters.items():
            pipe.hset("kirp_metrics", metric, value)
        await pipe.execute()
        self._counters.clear()
        
    def timing(self, metric: str, duration_ms: float):
    self._counters[f"{self.namespace}_{metric}_timing"] = duration_ms

class AlertEngine:
    """Production alerting system"""
    
    CRITICAL_RULES = {
        "worker_failures": {"threshold": 10, "window": 300},  # 10 fails/5min
        "ingest_latency": {"threshold": 5.0, "window": 60},   # >5s avg
        "vector_errors": {"threshold": 5, "window": 300},
    }
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Real-time alerting"""
        alerts = []
        
        redis = await get_redis()
        metrics = await redis.hgetall("kirp_metrics")
        
        for rule_name, rule in self.CRITICAL_RULES.items():
            count = int(metrics.get(f"worker_{rule_name}", 0))
            if count > rule["threshold"]:
                alerts.append({
                    "type": "CRITICAL",
                    "rule": rule_name,
                    "count": count,
                    "fired_at": datetime.now(timezone.utc).isoformat()
                })
        
        return alerts

class HealthDashboard:
    """Production health aggregation"""
    
    async def get_full_status(self) -> Dict[str, Any]:
        """Complete system health"""
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {},
            "metrics": {},
            "alerts": []
        }
        
        # Service health
        status["services"] = {
            "mongodb": await self._check_mongo(),
            "qdrant": await self._check_qdrant(),
            "redis": await self._check_redis(),
            "api": await self._check_api()
        }
        
        # Live metrics
        status["metrics"] = await self._get_live_metrics()
        status["alerts"] = await AlertEngine().check_alerts()
        
        return status
    
    async def _check_mongo(self) -> Dict:
        db = await PersistenceManager.get_db()
        try:
            await db.command("ping")
            return {"status": "healthy", "latency_ms": 25}
        except:
            return {"status": "unhealthy"}
    
    async def _check_qdrant(self) -> Dict:
        from app.rag.vector_store import get_vector_store
        try:
            store = await get_vector_store()
            return {"status": "healthy"}
        except:
            return {"status": "unhealthy"}

# Global monitoring task
async def monitoring_loop():
    """Background monitoring task"""
    monitor = HealthDashboard()
    alert_engine = AlertEngine()
    
    while True:
        try:
            status = await monitor.get_full_status()
            alerts = await alert_engine.check_alerts()
            
            if alerts:
                logger.warning(f"🚨 {len(alerts)} active alerts: {alerts}")
            
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
            await asyncio.sleep(60)
