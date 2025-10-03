"""
Background Sync Manager for Product Adder
Handles asynchronous synchronization of product data
"""

import threading
import time
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
from data_sync import DataSyncManager

logger = logging.getLogger(__name__)

class BackgroundSyncManager:
    """Manages background synchronization of product data"""
    
    def __init__(self):
        self.sync_manager = DataSyncManager()
        self.pending_syncs: Set[str] = set()
        self.completed_syncs: Set[str] = set()
        self.failed_syncs: Dict[str, str] = {}
        self.sync_lock = threading.Lock()
        self.worker_thread = None
        self.running = False
        
    def start_worker(self):
        """Start the background worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Background sync worker started")
    
    def stop_worker(self):
        """Stop the background worker thread"""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            logger.info("Background sync worker stopped")
    
    def _worker_loop(self):
        """Main worker loop for processing sync requests"""
        while self.running:
            try:
                with self.sync_lock:
                    if self.pending_syncs:
                        sku = self.pending_syncs.pop()
                        logger.info(f"Processing background sync for SKU: {sku}")
                        
                        try:
                            # Sync the specific SKU
                            result = self.sync_manager.shopify_client.sync_products([sku])
                            
                            if result.get('success', False):
                                self.completed_syncs.add(sku)
                                logger.info(f"Background sync completed for SKU: {sku}")
                            else:
                                self.failed_syncs[sku] = result.get('message', 'Unknown error')
                                logger.error(f"Background sync failed for SKU {sku}: {result.get('message')}")
                                
                        except Exception as e:
                            self.failed_syncs[sku] = str(e)
                            logger.error(f"Background sync error for SKU {sku}: {e}")
                
                # Sleep briefly to prevent excessive CPU usage
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Background sync worker error: {e}")
                time.sleep(1)
    
    def request_sync(self, sku: str) -> bool:
        """Request background sync for a specific SKU"""
        with self.sync_lock:
            if sku not in self.completed_syncs and sku not in self.pending_syncs:
                self.pending_syncs.add(sku)
                self.start_worker()  # Ensure worker is running
                logger.info(f"Background sync requested for SKU: {sku}")
                return True
            return False
    
    def get_sync_status(self, sku: str) -> str:
        """Get sync status for a specific SKU"""
        with self.sync_lock:
            if sku in self.completed_syncs:
                return 'completed'
            elif sku in self.pending_syncs:
                return 'pending'
            elif sku in self.failed_syncs:
                return 'failed'
            else:
                return 'not_requested'
    
    def get_sync_error(self, sku: str) -> Optional[str]:
        """Get sync error message for a specific SKU"""
        with self.sync_lock:
            return self.failed_syncs.get(sku)
    
    def clear_completed_syncs(self):
        """Clear completed syncs to free memory"""
        with self.sync_lock:
            self.completed_syncs.clear()
            logger.info("Cleared completed syncs")
    
    def cleanup_old_syncs(self, max_age_hours: int = 24):
        """Clean up old sync records to prevent memory leaks"""
        # This is a placeholder for future implementation
        # Could track timestamps and remove old records
        pass

# Global background sync manager instance
background_sync_manager = BackgroundSyncManager()
