User guide
==========

The task dispenser allows you to accumulate tasks and send them for processing in batches. For this, a server process is used that waits for tasks to appear in the redis queue. If more than a certain number of tasks appear in the queue or after a certain time, the batch of tasks is processed. Processing occurs in a pool of workers.

In order to send a task for review, a dispenser client is used. It connects to redis and allows you to put new tasks in the queue.

A standard use case is saving tasks to a database. Let's assume that you have a web server that implements an API with saving objects to a database. You need to save a lot of objects with a large rps. At the same time, you do not care about instant saving and in order to reduce the load on the web server and the database, you want to combine objects into batches for using bulk operations. To do this, you start a task dispenser server and send tasks for saving through the dispenser client (or directly to redis). The Dispenser server combines tasks into batches and, when several hundred objects have accumulated, sends them for storage.

A simple scheme assumes that heavy task processing is performed separately (for example, in Celery), then the number of workers in the pool can be small (or even equal to one), and the dispenser itself is quite lightweight. If there are too many tasks, then the main dispenser flow can be parallelized. To do this, you need to create several queues so that clients evenly distribute tasks between them. On the server side, raise several dispenser instances so that each processes its own queue.


Basic usage
-----------

Start dispenser with three queues `q1`, `q2`, `q3`:
* Queue `q1` handles serves tasks by calling the builtin `print` function.
* Queue `q2` handles serves tasks by calling the `failed_task` function from module `task_dispenser.utils`.
* Queue `q3` handles serves tasks by calling the `task_func` function from file `examples/simple_task.py`.

Run redis server automatically using default address.

.. code-block:: console

   $ task-dispenser start \
       -t q1 print \
       -t q2 task_dispenser.utils:failed_task \
       -t q3 examples/simple_task.py:task_func \
       --redis-start --procs-number 2 --on-error=log --batch-size=3 --log-level=debug

Then add task with `args=(1,)` to queue `q1` and task with `args=(2,)` to queue `q2` 5 times using default redis address:

.. code-block:: console

   $ task-dispenser add -t q1 1 -t q2 2 -t q3 3 -n 5 --log-level=debug

From code
---------

The same results can be achieved using following code:

Server:

.. code-block:: python
   :linenos:

   from task_dispenser import Dispenser
   import task_dispenser

   dispenser = Dispenser(
       tasks={
           'q1': print,
           'q2': task_dispenser.utils.failed_task,
           'q3': task_dispenser.utils.import_by_name('examples/simple_task.py:task_func'),
       },
       batch_size=3,
       flush_interval=5,
       redis_start=True,
       procs_number=2,
       on_error='fail',
   )

   with dispenser:
       dispenser.run()

Client:

.. code-block:: python
   :linenos:

   from task_dispenser import DispenserClient

   client = DispenserClient()
   client.add(qname='q1', task_args=(1,))

Docker
------

You can use docker or docker-compose, so redis server can be started as separate service:

.. literalinclude:: ../../docker-compose.yml
   :language: yaml

.. code-block:: console
   
   $ docker run --net=host --rm --name=task_dispenser \
       ghcr.io/blopser/task_dispenser task-dispenser \
       add -t q1 1 -t q3 3 -n 5 \
       --log-level=debug --redis-host=localhost --redis-pass pass --redis-port=6379                                 
