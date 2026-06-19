from datetime import datetime, date


def now() -> datetime:
    return datetime.now()


def utcnow() -> datetime:
    return datetime.utcnow()


def today() -> date:
    return date.today()


def utcnow_callable():
    return utcnow()


def now_callable():
    return now()
