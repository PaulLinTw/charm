from celery.schedules import crontab
from configs.config import REDIS_HOST, REDIS_PORT, REDIS_DB

imports = (
    'async.tasks',
)

broker_url = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
result_backend = f'redis://{REDIS_HOST}:{REDIS_PORT}'
timezone = "Asia/Taipei"
worker_max_tasks_per_child = 10

# worker_send_task_events = True

beat_schedule = {
    # Executes every 1 minute
    "get_metrics_from_vhosts": {
        'task': 'async.tasks.get_metrics',
        'schedule': crontab(minute='*'),
        # 'args': []  # 10 days before
    },
    # Executes every 1 minute
    "get_vagrant_status_from_vhosts": {
        'task': 'async.tasks.get_vagrant_status',
        'schedule': crontab(minute='*/3'),
        # 'args': []  # 10 days before
    }
}
