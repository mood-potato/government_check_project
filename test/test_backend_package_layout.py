import importlib.util


def test_modules_live_under_backend_package():
    assert importlib.util.find_spec("backend.modules") is not None
    assert importlib.util.find_spec("modules") is None
