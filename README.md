# Task dispenser

asdf

<!--- End header --->

## Celery example
Run task dispenser with celery task
```bash
task-dispenser start \
    -t q1 examples/celery_task.py:task_func \
    -t q2 examples/celery_task.py:simple_celery_task_func.apply_async \
    --redis-start --procs-number 2 --on-error=log --batch-size=3 --log-level=debug &
```

Run celery worker with the same celery app
```bash
cd examples
celery -A celery_task worker
```

Add task to queue
```bash
task-dispenser add -t q1 1 -n 5 --log-level=debug
task-dispenser add -t q2 1 -n 5 --log-level=debug
```

## Development
```bash
redis-server
watchmedo auto-restart --directory=./task_dispenser --directory=./examples --pattern=*.py --recursive --
```
