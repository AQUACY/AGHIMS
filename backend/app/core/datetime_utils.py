"""
Date and time utility functions that support application reference date override.

This module provides date/time functions that can use a configured reference date
instead of the system date. This is useful when the system date is changed for
testing or working with historical data, but the application should continue
using the original current date.

Usage:
    from app.core.datetime_utils import now, utcnow, today
    
    # These functions will use APPLICATION_REFERENCE_DATE if configured,
    # otherwise they use the system date
    current_time = now()
    current_utc = utcnow()
    current_date = today()
"""
from datetime import datetime, date, timedelta
from typing import Optional
from app.core.config import settings


# Cache for parsed reference date to avoid repeated parsing
_cached_reference_datetime: Optional[datetime] = None
_cached_reference_date: Optional[date] = None
_reference_date_set_at: Optional[datetime] = None  # When the reference date was first set


def _parse_reference_date() -> Optional[datetime]:
    """Parse the APPLICATION_REFERENCE_DATE setting into a datetime object."""
    global _cached_reference_datetime, _reference_date_set_at
    
    if not settings.APPLICATION_REFERENCE_DATE:
        _cached_reference_datetime = None
        _reference_date_set_at = None
        return None
    
    try:
        ref_date_str = settings.APPLICATION_REFERENCE_DATE.strip()
        
        # Try parsing with time first
        try:
            parsed = datetime.strptime(ref_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Try parsing date only
            try:
                parsed = datetime.strptime(ref_date_str, "%Y-%m-%d")
                # If only date provided, use current time of day
                now = datetime.now()
                parsed = parsed.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)
            except ValueError:
                # Try other common formats
                try:
                    parsed = datetime.strptime(ref_date_str, "%Y-%m-%d %H:%M")
                    now = datetime.now()
                    parsed = parsed.replace(second=now.second, microsecond=now.microsecond)
                except ValueError:
                    return None
        
        # Store when we first set the reference date (only set once)
        if _reference_date_set_at is None:
            _reference_date_set_at = datetime.now()
        
        _cached_reference_datetime = parsed
        return parsed
    except Exception:
        return None


def _get_reference_date() -> Optional[date]:
    """Get the reference date (date only) from the configuration."""
    global _cached_reference_date
    
    ref_datetime = _parse_reference_date()
    if ref_datetime:
        _cached_reference_date = ref_datetime.date()
        return _cached_reference_date
    else:
        _cached_reference_date = None
        return None


def now() -> datetime:
    """
    Get current datetime (local timezone).
    
    If APPLICATION_REFERENCE_DATE is configured, returns that date/time
    adjusted by the difference between the current system time and when
    the reference date was set. This allows the date to progress automatically.
    
    Example:
        - Reference date set to 2025-10-20 when system date was 2025-10-20
        - Tomorrow (system date 2025-10-21): returns 2025-10-21
        - The date progresses automatically based on system date changes
    
    Returns:
        datetime: Current datetime (using reference date if configured, progressing automatically)
    """
    ref_datetime = _parse_reference_date()
    if ref_datetime and _reference_date_set_at:
        # Calculate how many days have passed since reference date was set
        system_now = datetime.now()
        days_passed = (system_now.date() - _reference_date_set_at.date()).days
        
        # Add the days to the reference date to make it progress
        from datetime import timedelta
        progressed_date = ref_datetime + timedelta(days=days_passed)
        
        # Use the progressed date but with current time
        return progressed_date.replace(
            hour=system_now.hour,
            minute=system_now.minute,
            second=system_now.second,
            microsecond=system_now.microsecond
        )
    elif ref_datetime:
        # Fallback: if _reference_date_set_at is not set, use fixed date with current time
        system_now = datetime.now()
        return ref_datetime.replace(
            hour=system_now.hour,
            minute=system_now.minute,
            second=system_now.second,
            microsecond=system_now.microsecond
        )
    return datetime.now()


def utcnow() -> datetime:
    """
    Get current UTC datetime.
    
    If APPLICATION_REFERENCE_DATE is configured, converts the reference
    date to UTC and adjusts time to current UTC time. The date progresses
    automatically based on system date changes.
    
    Returns:
        datetime: Current UTC datetime (using reference date if configured, progressing automatically)
    """
    ref_datetime = _parse_reference_date()
    if ref_datetime and _reference_date_set_at:
        # Calculate how many days have passed since reference date was set
        system_now = datetime.now()
        days_passed = (system_now.date() - _reference_date_set_at.date()).days
        
        # Add the days to the reference date
        from datetime import timedelta
        progressed_date = ref_datetime + timedelta(days=days_passed)
        
        # Convert to UTC
        system_utc = datetime.utcnow()
        system_local = datetime.now()
        
        # Calculate timezone offset
        offset = system_local - system_utc
        
        # Apply progressed date with current UTC time
        ref_utc = progressed_date - offset
        return ref_utc.replace(
            hour=system_utc.hour,
            minute=system_utc.minute,
            second=system_utc.second,
            microsecond=system_utc.microsecond
        )
    elif ref_datetime:
        # Fallback: fixed date with current UTC time
        system_utc = datetime.utcnow()
        system_local = datetime.now()
        offset = system_local - system_utc
        ref_utc = ref_datetime - offset
        return ref_utc.replace(
            hour=system_utc.hour,
            minute=system_utc.minute,
            second=system_utc.second,
            microsecond=system_utc.microsecond
        )
    return datetime.utcnow()


def today() -> date:
    """
    Get current date.
    
    If APPLICATION_REFERENCE_DATE is configured, returns the date portion
    of the progressed reference date. The date progresses automatically.
    
    Returns:
        date: Current date (using reference date if configured, progressing automatically)
    """
    # Use now() to get the progressed datetime, then extract date
    current_datetime = now()
    ref_datetime = _parse_reference_date()
    if ref_datetime:
        return current_datetime.date()
    return date.today()


def clear_cache():
    """
    Clear the cached reference date/datetime.
    
    Call this if APPLICATION_REFERENCE_DATE is changed at runtime
    (though it's recommended to restart the application instead).
    """
    global _cached_reference_datetime, _cached_reference_date, _reference_date_set_at
    _cached_reference_datetime = None
    _cached_reference_date = None
    _reference_date_set_at = None


# Callable functions for SQLAlchemy defaults
def utcnow_callable():
    """
    Callable function for SQLAlchemy DateTime defaults.
    
    Usage in models:
        created_at = Column(DateTime, default=utcnow_callable)
    
    Returns:
        datetime: Current UTC datetime (using reference date if configured)
    """
    return utcnow()


def now_callable():
    """
    Callable function for SQLAlchemy DateTime defaults (local time).
    
    Usage in models:
        created_at = Column(DateTime, default=now_callable)
    
    Returns:
        datetime: Current local datetime (using reference date if configured)
    """
    return now()

