import time
import logging
from typing import Dict, Any
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MetricsTracker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize metrics storage"""
        self.metrics = {
            'query_count': 0,
            'error_count': 0,
            'total_query_time': 0.0,
            'avg_query_time': 0.0,
            'slow_queries': 0,
            'queries_per_minute': {},
            'errors_per_minute': {},
        }
        self.slow_query_threshold = 1.0
        
    def record_query(self, query_time: float, error: bool = False) -> None:
        """Record a query execution"""
        current_minute = datetime.now().replace(second=0, microsecond=0)
        
        self.metrics['query_count'] += 1
        self.metrics['total_query_time'] += query_time
        self.metrics['avg_query_time'] = (
            self.metrics['total_query_time'] / self.metrics['query_count']
        )
        
        # Record slow queries
        if query_time > self.slow_query_threshold:
            self.metrics['slow_queries'] += 1
            
        # Update queries per minute
        if current_minute not in self.metrics['queries_per_minute']:
            self.metrics['queries_per_minute'][current_minute] = 0
        self.metrics['queries_per_minute'][current_minute] += 1
        
        # Record errors if any
        if error:
            self.metrics['error_count'] += 1
            if current_minute not in self.metrics['errors_per_minute']:
                self.metrics['errors_per_minute'][current_minute] = 0
            self.metrics['errors_per_minute'][current_minute] += 1
            
        # Clean up old minute-based metrics (keep last hour)
        self._cleanup_old_metrics()
        
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than 1 hour"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        self.metrics['queries_per_minute'] = {
            k: v for k, v in self.metrics['queries_per_minute'].items()
            if k > cutoff_time
        }
        
        self.metrics['errors_per_minute'] = {
            k: v for k, v in self.metrics['errors_per_minute'].items()
            if k > cutoff_time
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics
        
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self._initialize()


def track_query_metrics(func):
    """Decorator to track query execution metrics"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        error = False
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = True
            raise
        finally:
            query_time = time.time() - start_time
            MetricsTracker().record_query(query_time, error)
    return wrapper 