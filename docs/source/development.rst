Development build
=================

Start development container, install library in editable mode and run tests:

.. code-block:: console

   $ make start
   $ python -m pip install -e .[dev]
   $ /bin/bash ./scripts/test.sh
