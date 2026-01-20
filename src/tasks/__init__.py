# Celery Tasks
from .notification_tasks import celery_app

# Export celery_app as 'celery' for CLI compatibility (celery -A src.tasks worker)
celery = celery_app
