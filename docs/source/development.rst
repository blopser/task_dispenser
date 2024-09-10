Development build
=================

1) start development container, install library in editable mode and run tests::

  $ make start
  $ python -m pip install -e .[dev]
  $ /bin/bash ./scripts/test.sh
