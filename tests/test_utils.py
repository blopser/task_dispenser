from task_dispenser.utils import import_by_name


def test_import_by_name() -> None:
    assert import_by_name('print') is print
