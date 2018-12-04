#export C_FORCE_ROOT='true'
REDIS_HOST='192.168.1.207'
#cd /app/
celery -A async.tasks.celery worker --broker="redis://${REDIS_HOST}:6379/3" --loglevel=debug
