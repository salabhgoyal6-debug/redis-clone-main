# redis-clone

A from-scratch implementation of Redis's core functionality in Python, built to
understand networking, protocol design, and concurrency at a low level.

## Features
- Raw TCP server implementing the real RESP (REdis Serialization Protocol)
- Compatible with real `redis-cli` and Redis client libraries
- Commands: GET, SET, DEL, EXPIRE, TTL, LPUSH, RPUSH, LPOP, RPOP, LRANGE
- Thread-per-client concurrency with lock-protected shared state
- Lazy + active key expiration
- Disk persistence (JSON snapshotting) surviving server restarts

## Running it
\`\`\`bash
python server.py
\`\`\`
Then connect with `redis-cli -p 6380` or any Redis client library.

## Running tests
\`\`\`bash
pip install pytest
pytest -v
\`\`\`

## What I learned building this
- How TCP sockets and byte-stream parsing actually work under the hood
- Protocol design (RESP) — why length-prefixed fields make parsing unambiguous
- Race conditions and locking in multi-threaded servers
- Tradeoffs between lazy vs. active expiration strategies
- Why absolute timestamps (not countdowns) make persistence and expiry compose correctly
