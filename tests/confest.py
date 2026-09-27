import os 
import pytest

@pytest.fixture(autouse=True)
def cleanup_test_files():
    yield
    if os.path.exists("test_dump.json"):
        os.remove("test_dump.json")