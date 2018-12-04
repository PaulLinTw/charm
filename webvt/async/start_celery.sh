export C_FORCE_ROOT='true'
REDIS_HOST='192.168.1.207'
cd /app/
celery -A async.tasks.celery worker --broker="redis://${REDIS_HOST}:6379/0" --loglevel=debug
echo celery -A async.tasks.celery beat -l info
echo celery -A async.tasks.celery worker -l debug