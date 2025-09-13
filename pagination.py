"""
Pagination utilities for Product Adder
Handles pagination for large product lists and API responses
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class PaginationInfo:
    """Pagination information"""
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int]
    prev_page: Optional[int]

class Paginator:
    """Handles pagination for data sets"""
    
    def __init__(self, data: List[Any], page: int = 1, per_page: int = 20, max_per_page: int = 100):
        """
        Initialize paginator
        
        Args:
            data: List of data to paginate
            page: Current page number (1-based)
            per_page: Number of items per page
            max_per_page: Maximum allowed items per page
        """
        self.data = data
        self.total = len(data)
        self.page = max(1, page)
        self.per_page = min(per_page, max_per_page)
        self.total_pages = math.ceil(self.total / self.per_page) if self.total > 0 else 1
        
        # Ensure page is within bounds
        if self.page > self.total_pages:
            self.page = self.total_pages
    
    def get_page_data(self) -> List[Any]:
        """Get data for current page"""
        if self.total == 0:
            return []
        
        start_index = (self.page - 1) * self.per_page
        end_index = start_index + self.per_page
        
        return self.data[start_index:end_index]
    
    def get_pagination_info(self) -> PaginationInfo:
        """Get pagination information"""
        return PaginationInfo(
            page=self.page,
            per_page=self.per_page,
            total=self.total,
            total_pages=self.total_pages,
            has_next=self.page < self.total_pages,
            has_prev=self.page > 1,
            next_page=self.page + 1 if self.page < self.total_pages else None,
            prev_page=self.page - 1 if self.page > 1 else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pagination info to dictionary"""
        info = self.get_pagination_info()
        return {
            'page': info.page,
            'per_page': info.per_page,
            'total': info.total,
            'total_pages': info.total_pages,
            'has_next': info.has_next,
            'has_prev': info.has_prev,
            'next_page': info.next_page,
            'prev_page': info.prev_page,
            'data': self.get_page_data()
        }

def paginate_data(data: List[Any], page: int = 1, per_page: int = 20, 
                 max_per_page: int = 100) -> Dict[str, Any]:
    """
    Paginate a list of data
    
    Args:
        data: List of data to paginate
        page: Current page number (1-based)
        per_page: Number of items per page
        max_per_page: Maximum allowed items per page
        
    Returns:
        Dictionary with paginated data and pagination info
    """
    paginator = Paginator(data, page, per_page, max_per_page)
    return paginator.to_dict()

def paginate_query(query_func, page: int = 1, per_page: int = 20, 
                  max_per_page: int = 100, **query_kwargs) -> Dict[str, Any]:
    """
    Paginate a database query
    
    Args:
        query_func: Function that returns (data, total_count)
        page: Current page number (1-based)
        per_page: Number of items per page
        max_per_page: Maximum allowed items per page
        **query_kwargs: Additional arguments to pass to query_func
        
    Returns:
        Dictionary with paginated data and pagination info
    """
    per_page = min(per_page, max_per_page)
    offset = (page - 1) * per_page
    
    # Get data and total count
    data, total = query_func(offset=offset, limit=per_page, **query_kwargs)
    
    # Calculate pagination info
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev,
        'next_page': page + 1 if has_next else None,
        'prev_page': page - 1 if has_prev else None,
        'data': data
    }

def create_pagination_links(base_url: str, page: int, total_pages: int, 
                          per_page: int, **params) -> Dict[str, Optional[str]]:
    """
    Create pagination links for API responses
    
    Args:
        base_url: Base URL for the endpoint
        page: Current page number
        total_pages: Total number of pages
        per_page: Items per page
        **params: Additional query parameters
        
    Returns:
        Dictionary with pagination links
    """
    def build_url(page_num: Optional[int]) -> Optional[str]:
        if page_num is None:
            return None
        
        query_params = {
            'page': page_num,
            'per_page': per_page,
            **params
        }
        
        param_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
        return f"{base_url}?{param_string}"
    
    return {
        'first': build_url(1) if page > 1 else None,
        'prev': build_url(page - 1) if page > 1 else None,
        'next': build_url(page + 1) if page < total_pages else None,
        'last': build_url(total_pages) if page < total_pages else None,
        'current': build_url(page)
    }

def validate_pagination_params(page: int, per_page: int, max_per_page: int = 100) -> Tuple[int, int]:
    """
    Validate and sanitize pagination parameters
    
    Args:
        page: Page number
        per_page: Items per page
        max_per_page: Maximum allowed items per page
        
    Returns:
        Tuple of (validated_page, validated_per_page)
    """
    # Ensure page is at least 1
    page = max(1, page)
    
    # Ensure per_page is within bounds
    per_page = max(1, min(per_page, max_per_page))
    
    return page, per_page

def get_pagination_metadata(page: int, per_page: int, total: int) -> Dict[str, Any]:
    """
    Get pagination metadata
    
    Args:
        page: Current page number
        per_page: Items per page
        total: Total number of items
        
    Returns:
        Dictionary with pagination metadata
    """
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    start_item = (page - 1) * per_page + 1 if total > 0 else 0
    end_item = min(page * per_page, total)
    
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'start_item': start_item,
        'end_item': end_item,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'is_first_page': page == 1,
        'is_last_page': page == total_pages
    }
