# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
try:
    from .celery import app as celery_app
except ImportError:
    # Celery is optional for development
    pass

__all__ = ('celery_app',) if 'celery_app' in locals() else ()
