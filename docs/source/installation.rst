Installation
============

Docker container
----------------

Install `docker <https://www.docker.com/products/overview>`_, `podman <https://podman.io/>`_ (or any other container runtime) and use ``ghcr.io/blopser/task_dispenser``. Docker entrypoint is task_dispenser executable so you may just run it to start test:

.. code-block:: console

   $ docker run \
       --replace --network=host --name task_dispenser_cli -it \
       ghcr.io/blopser/task_dispenser \
       add -t q1 1 --redis-start --redis-pass pass

Or clone the repository of this project and build it manually:

.. code-block:: console

   $ git clone ...
   $ cd task_dispenser
   $ docker build . -t task-dispenser
   $ docker run \
       --replace --name task_dispenser -p 6379:6379 -it \
       --volume ./examples:/home/user/app/examples \
       localhost/task-dispenser:latest \
       start -t q1 examples/simple_task.py:task_func --redis-start --redis-pass pass

Pip library
-----------

If you don't have container in your environment or need this package as a python library then preffered installation method is by using `pip <http://pypi.python.org/pypi/pip/>`_

.. code-block:: console

   $ pip install task_dispenser

If you don't have pip installed, you can easily install it by downloading and running `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_.

If, for some reason, pip won't work, you can manually download the Task dispenser distribution from github and then install it:

.. code-block:: console

   $ git clone ...
   $ cd task_dispenser
   $ python -m pip install .
