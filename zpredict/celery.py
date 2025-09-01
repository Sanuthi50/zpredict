import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')

app = Celery('zpredict')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Optional: Configure some Celery settings here if needed
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
