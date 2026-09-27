import time
import pytest
from store import Store

@pytest.fixture 
def store():
    # a fresh store for every test, using a temp file so tests dont pollute 
    s = Store(filepath="test_dump.json")
    yield s 
    
def test_set_and_get(store):
    store.execute(["SET", "name", "adi"])
    result = store.execute(["GET", "name"])
    assert result == ("bulk", "adi")

def test_get_missing_key_returns_nil(store):
    result = store.execute(["GET", "nonexistent"])
    assert result == ("bulk", None)
    
def test_del_returns_count(store):
    store.execute(["SET", "a", "1"])
    store.execute(["SET", "b", "2"])
    result = store.execute(["DELETE", "a", "b", "c"])
    assert result == ("integer", 2)
    
def test_expired_and_ttl(store):
    store.execute(["SET", "session", "abc"])
    store.execute(["EXPIRE", "session", "100"])
    result = store.execute(["TTL", "session"])
    assert result[0] == "integer"
    assert 95 <= result[1] <= 100   # allow small timing variance

def test_expired_key_returns_nil(store):
    store.execute(["SET", "temp", "val"])
    store.execute(["EXPIRE", "temp", "-1"])  # already expired
    result = store.execute(["GET", "temp"])
    assert result == ("bulk", None)

def test_rpush_and_lrange(store):
    store.execute(["RPUSH", "mylist", "a", "b", "c"])
    result = store.execute(["LRANGE", "mylist", "0", "-1"])
    assert result == ("array", ["a", "b", "c"])

def test_lpush_reverses_order(store):
    store.execute(["LPUSH", "mylist", "a", "b", "c"])
    result = store.execute(["LRANGE", "mylist", "0", "-1"])
    assert result == ("array", ["c", "b", "a"])

def test_wrongtype_error(store):
    store.execute(["SET", "mystring", "hello"])
    result = store.execute(["LPUSH", "mystring", "x"])
    assert result[0] == "error"
    assert "WRONGTYPE" in result[1]

def test_unknown_command(store):
    result = store.execute(["FOOBAR"])
    assert result[0] == "error"