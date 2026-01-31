import logging
import time
from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
from rest_framework import status
import re


logger = logging.getLogger(__name__)


class PokeAPIError(Exception):
    """Custom exception for PokeAPI related errors"""
    pass


def validate_pokemon_name(name):
    """Validate Pokemon name input"""
    if not name or not isinstance(name, str):
        raise ValidationError("Pokemon name must be a non-empty string")
    
    # Remove extra whitespace and convert to lowercase
    name = name.strip().lower()
    
    # Basic validation - only letters, numbers, and hyphens allowed
    if not re.match(r'^[a-z0-9-]+$', name):
        raise ValidationError("Pokemon name can only contain letters, numbers, and hyphens")
    
    if len(name) > 100:
        raise ValidationError("Pokemon name too long")
    
    return name


def validate_team_names(team_names):
    """Validate a list of Pokemon team names"""
    if not isinstance(team_names, list):
        raise ValidationError("Team must be a list of names")
    
    if len(team_names) > 6:
        raise ValidationError("Team cannot have more than 6 Pokemon")
    
    validated_names = []
    for name in team_names:
        if name:  # Skip empty names
            validated_name = validate_pokemon_name(name)
            validated_names.append(validated_name)
    
    return validated_names


def validate_page_number(page):
    """Validate page number"""
    try:
        page = int(page)
        if page < 1:
            raise ValidationError("Page number must be at least 1")
        return page
    except (ValueError, TypeError):
        raise ValidationError("Invalid page number")


def validate_page_size(page_size):
    """Validate page size"""
    try:
        page_size = int(page_size)
        if page_size < 1:
            raise ValidationError("Page size must be at least 1")
        if page_size > 100:
            raise ValidationError("Page size cannot exceed 100")
        return page_size
    except (ValueError, TypeError):
        raise ValidationError("Invalid page size")


def sanitize_query_param(value, max_length=100):
    """Sanitize query parameters"""
    if not value:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    # Remove potentially harmful characters
    value = re.sub(r'[<>"\']', '', value)
    
    # Limit length
    value = value[:max_length].strip()
    
    return value


def log_api_request(view_func):
    """Decorator to log API requests"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        
        try:
            response = view_func(request, *args, **kwargs)
            status_code = getattr(response, 'status_code', 200)
        except Exception as e:
            logger.error(f"API request failed: {str(e)}", exc_info=True)
            response = JsonResponse(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            status_code = 500
        
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        # Log request details
        logger.info(
            f"{request.method} {request.get_full_path()} - "
            f"Status: {status_code}, "
            f"Response Time: {response_time_ms}ms, "
            f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]}"
        )
        
        return response
    
    return wrapper


def handle_api_errors(view_func):
    """Decorator to handle common API errors"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        
        except ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            return JsonResponse(
                {"error": "Validation failed", "details": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except PokeAPIError as e:
            logger.error(f"PokeAPI error: {str(e)}")
            return JsonResponse(
                {"error": "Pokemon API error", "details": str(e)}, 
                status=status.HTTP_502_BAD_GATEWAY
            )
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return wrapper


def cache_key_with_prefix(prefix, *args):
    """Generate consistent cache keys"""
    key_parts = [prefix] + [str(arg) for arg in args if arg is not None]
    return ":".join(key_parts)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rate_limit_key(request, limit_type):
    """Generate rate limit key for caching"""
    ip = get_client_ip(request)
    return f"rate_limit:{limit_type}:{ip}"


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        logger.info(f"{self.operation_name} completed in {duration:.3f}s")
        
        if exc_type:
            logger.error(f"{self.operation_name} failed with {exc_type.__name__}: {exc_val}")


def safe_json_loads(json_string, default=None):
    """Safely load JSON string"""
    try:
        import json
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default or {}


def safe_json_dumps(data, default=None):
    """Safely dump data to JSON string"""
    try:
        import json
        return json.dumps(data)
    except (TypeError, ValueError):
        return json.dumps(default or {})
