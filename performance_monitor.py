"""
Performance Monitor for Product Adder
Tracks performance metrics and provides monitoring endpoints
"""

import time
import threading
import logging
from functools import wraps
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class APIMetric:
    """API call performance metric"""
    endpoint: str
    method: str
    duration: float
    status_code: int
    timestamp: datetime
    error: Optional[str] = None

class PerformanceMonitor:
    """Monitors and tracks performance metrics"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.api_metrics: deque = deque(maxlen=max_metrics)
        self.lock = threading.RLock()
        self.start_time = datetime.utcnow()
        
        # Performance counters
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)
        
        # Error tracking
        self.errors = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        
        # API rate limiting tracking
        self.api_calls = defaultdict(int)
        self.api_errors = defaultdict(int)
        
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a performance metric"""
        with self.lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=datetime.utcnow(),
                tags=tags or {}
            )
            self.metrics.append(metric)
            
            # Update counters and gauges
            if name.endswith('_count'):
                self.counters[name] += int(value)
            elif name.endswith('_timer'):
                self.timers[name].append(value)
            else:
                self.gauges[name] = value
    
    def record_api_call(self, endpoint: str, method: str, duration: float, 
                       status_code: int, error: Optional[str] = None) -> None:
        """Record an API call metric"""
        with self.lock:
            api_metric = APIMetric(
                endpoint=endpoint,
                method=method,
                duration=duration,
                status_code=status_code,
                timestamp=datetime.utcnow(),
                error=error
            )
            self.api_metrics.append(api_metric)
            
            # Update counters
            self.api_calls[f"{method}:{endpoint}"] += 1
            if error or status_code >= 400:
                self.api_errors[f"{method}:{endpoint}"] += 1
    
    def record_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Record an error"""
        with self.lock:
            error_data = {
                'type': error_type,
                'message': error_message,
                'context': context or {},
                'timestamp': datetime.utcnow()
            }
            self.errors.append(error_data)
            self.error_counts[error_type] += 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self.lock:
            current_time = datetime.utcnow()
            uptime = (current_time - self.start_time).total_seconds()
            
            # Calculate averages for timers
            timer_averages = {}
            for name, values in self.timers.items():
                if values:
                    timer_averages[name] = {
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
            
            return {
                'uptime_seconds': uptime,
                'uptime_human': str(timedelta(seconds=int(uptime))),
                'total_metrics': len(self.metrics),
                'total_api_calls': len(self.api_metrics),
                'total_errors': len(self.errors),
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'timer_averages': timer_averages,
                'error_counts': dict(self.error_counts),
                'api_call_counts': dict(self.api_calls),
                'api_error_counts': dict(self.api_errors)
            }
    
    def get_recent_metrics(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get metrics from the last N minutes"""
        with self.lock:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            recent_metrics = [
                {
                    'name': m.name,
                    'value': m.value,
                    'timestamp': m.timestamp.isoformat(),
                    'tags': m.tags
                }
                for m in self.metrics
                if m.timestamp >= cutoff_time
            ]
            return recent_metrics
    
    def get_recent_api_calls(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get API calls from the last N minutes"""
        with self.lock:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            recent_calls = [
                {
                    'endpoint': m.endpoint,
                    'method': m.method,
                    'duration': m.duration,
                    'status_code': m.status_code,
                    'timestamp': m.timestamp.isoformat(),
                    'error': m.error
                }
                for m in self.api_metrics
                if m.timestamp >= cutoff_time
            ]
            return recent_calls
    
    def get_recent_errors(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get errors from the last N minutes"""
        with self.lock:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            recent_errors = [
                {
                    'type': e['type'],
                    'message': e['message'],
                    'context': e['context'],
                    'timestamp': e['timestamp'].isoformat()
                }
                for e in self.errors
                if e['timestamp'] >= cutoff_time
            ]
            return recent_errors
    
    def get_performance_health(self) -> Dict[str, Any]:
        """Get overall performance health status"""
        with self.lock:
            # Calculate health scores
            health_scores = {}
            
            # API health (based on error rate)
            total_api_calls = sum(self.api_calls.values())
            total_api_errors = sum(self.api_errors.values())
            api_error_rate = (total_api_errors / total_api_calls * 100) if total_api_calls > 0 else 0
            health_scores['api'] = max(0, 100 - api_error_rate)
            
            # Error health (based on recent errors)
            recent_errors = len(self.get_recent_errors(5))
            health_scores['errors'] = max(0, 100 - (recent_errors * 10))  # 10 points per error
            
            # Response time health (based on recent API calls)
            recent_calls = self.get_recent_api_calls(5)
            if recent_calls:
                avg_duration = sum(call['duration'] for call in recent_calls) / len(recent_calls)
                # Score decreases as response time increases
                health_scores['response_time'] = max(0, 100 - (avg_duration * 10))
            else:
                health_scores['response_time'] = 100

            # Overall health (average of all scores)
            overall_health = sum(health_scores.values()) / len(health_scores) if health_scores else 100
            
            # Overall health (average of all scores)
            overall_health = sum(health_scores.values()) / len(health_scores)
            
            return {
                'overall_health': round(overall_health, 1),
                'health_scores': {k: round(v, 1) for k, v in health_scores.items()},
                'status': 'healthy' if overall_health >= 80 else 'degraded' if overall_health >= 60 else 'unhealthy',
                'api_error_rate': round(api_error_rate, 2),
                'recent_errors': recent_errors
            }
    
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        with self.lock:
            self.metrics.clear()
            self.api_metrics.clear()
            self.errors.clear()
            self.counters.clear()
            self.timers.clear()
            self.gauges.clear()
            self.api_calls.clear()
            self.api_errors.clear()
            self.error_counts.clear()
            self.start_time = datetime.utcnow()

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def record_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """Record a performance metric"""
    performance_monitor.record_metric(name, value, tags)

def record_api_call(endpoint: str, method: str, duration: float, 
                   status_code: int, error: Optional[str] = None) -> None:
    """Record an API call metric"""
    performance_monitor.record_api_call(endpoint, method, duration, status_code, error)

def record_error(error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Record an error"""
    performance_monitor.record_error(error_type, error_message, context)

def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    return performance_monitor.get_metrics_summary()

def get_performance_health() -> Dict[str, Any]:
    """Get performance health status"""
    return performance_monitor.get_performance_health()

# Performance timing decorator
def time_function(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to time function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                record_metric(f"{metric_name}_duration", duration, tags)
                record_metric(f"{metric_name}_success_count", 1, tags)
                return result
            except Exception as e:
                duration = time.time() - start_time
                record_metric(f"{metric_name}_duration", duration, tags)
                record_metric(f"{metric_name}_error_count", 1, tags)
                record_error(f"{metric_name}_error", str(e), {'function': func.__name__})
                raise
        return wrapper
    return decorator

# API timing decorator
def time_api_call(endpoint: str, method: str = "GET"):
    """Decorator to time API calls"""
    def decorator(func):
        @wraps(func)
        def timing_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                error = str(e)
                raise
            finally:
                duration = time.time() - start_time
                record_api_call(endpoint, method, duration, status_code, error)
        
        return timing_wrapper
    return decorator
