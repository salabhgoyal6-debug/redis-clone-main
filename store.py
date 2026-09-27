import threading
import time 
import json

class Store:
    def __init__(self, filepath="dump.json"):
        self.data = {} # the actual storage is just a dict 
        self.lock = threading.Lock() # it protects data from concurrent access 
        self.expires = {} # key -> absolute unix timestamp when it expires
        self.filepath = filepath
        self._load()
        
    def _load(self):
        # on startup, load data from disk if a snapshot file exists 
        try: 
            with open(self.filepath, "r") as f:
                saved = json.load(f)
                self.data = saved.get("data", {})
                self.expires = saved.get("expires", {})
            print(f"Loaded {len(self.data)} keys from {self.filepath}")
        except FileNotFoundError:
            print("No existing snapshot found, starting fresh")
    
    def save(self):
        # writing current state to disk
        with self.lock:
            with open(self.filepath, "w") as f:
                json.dump({"data" : self.data, "expires": self.expires}, f )
        print(f"Saved {len(self.data)} keys to {self.filepath}")
    
    def execute(self, command):
        if not command:
            return ("error", "ERR empty command")
        
        cmd_name = command[0].upper() # redis commands are insensitive
        args = command[1:]
        # suppose we have ["SET", "name", "alice"] so the cmd_name becomes SET and args will be ["name", "alice"]
        
        handler = getattr(self, f"cmd_{cmd_name.lower()}", None)
        if handler is None:
            return("error", f"ERR unknown command '{cmd_name}'")
        
        with self.lock:
            return handler(args)
        # suppose we have handler = slef.cmd_set, then it becomes self.cmd_set(args)
    
    def _is_expired(self, key):
        # check if the key has an expiry set and that time has passed or not ??
        expiry = self.expires.get(key)
        return expiry is not None and time.time() >= expiry
    
    def _expire_if_needed(self, key):
        # if the key has expired then remove it from the bioth the dict 
        if self._is_expired(key):
            self.data.pop(key, None)
            self.expires.pop(key, None)
            return True
        
        return False
        
    def _check_type(self, key, expected_type):
        if key not in self.data:
            return None
        if not isinstance(self.data[key], expected_type):
            return ("error", "WRONGTYPE Operation against a key holding the wrong kind of value")
        return None

    def cmd_set(self, args):
        if len(args) != 2:
            return ("error", "ERR wrong number of arguments for set command ")
        
        key, value = args 
        self.data[key] = value
        self.expires.pop(key, None)
        return ("simple", "ok")

    def cmd_get(self, args):
        if len(args) != 1:
            return ("ERROR", "ERR wrong number of arguments for 'get; command")
        
        key = args[0]
        self._expire_if_needed(key) # check before reading, this is the lazy part
        value = self.data.get(key)
        return ("bulk", value)
    
    def cmd_delete(self, args):
        if len(args) < 1 :
            return ("error", "ERR wrong number of arguments for 'del' command")
        deleted_count = 0 
        for key in args:
            if key in self.data:
                del self.data[key]
                self.expires.pop(key, None)
                deleted_count += 1
        return ("integer", deleted_count)
    
    def cmd_expire(self, args):
        if len(args) != 2 :
            return("error", "ERR wrong number of arguments for 'expire' command")
        
        key, seconds = args
        if self._expire_if_needed(key) or key not in self.data:
            return ("Integer", 0)
        try:
            seconds = int(seconds)
        except ValueError:
            return ("error", "err value is not an integer or out of range ")
        self.expires[key] = time.time() + seconds
        return ("integer", 1) 
    
    def cmd_ttl(self, args):
        if len(args) != 1 :
            return ("error", "err wrong number of arguments for 'ttl' command ")
        
        key = args[0]
        if self._expire_if_needed(key) or key not in self.data:
            return ("integer", -2) #key doesnot exist 
        expiry = self.expires.get(key)
        if expiry is None:
            return ("integer", -1 ) # -1 key exists but has no expiry set 
        remaining = int(expiry - time.time())
        return ("integer", max(remaining, 0))
    
    def start_active_expiry(self, interval=1.0):
        # it runs in background, periodically cleaning expired keys 
        def sweep():
            while True:
                time.sleep(interval)
                with self.lock:
                    expired_keys = [k for k in list(self.expires) if self._is_expired(k)]
                    for k in expired_keys:
                        self.data.pop(k, None)
                        self.expires.pop(k, None)
        thread = threading.Thread(target=sweep, daemon=True)
        thread.start()
    
    def cmd_lpush(self, args):
        if len(args) < 2 :
            return ("error", "err wrong number of arguments") 
        key, values = args[0], args[1:]
        
        self._expire_if_needed(key)
        type_error= self._check_type(key, list)
        if type_error:
            return type_error
        if key not in self.data:
            self.data[key] = []
        for v in values:
            self.data[key].insert(0, v) 
        
        return ("integer", len(self.data[key]))
    
    def cmd_rpush(self, args):
        if len(args) < 2 :
            return ("error", "ERR wrong number of arguments for 'rpush' command")
        key, values = args[0], args[1:]
        
        self._expire_if_needed(key)
        type_error = self._check_type(key, list)
        if type_error :
            return type_error
        if key not in self.data:
            self.data[key] = []
            
        self.data[key].extend(values) # append to the end 
        return ("integer", len(self.data[key]))
    
    def cmd_loop(self, args):
        if len(args) != 1:
            return ("error", "ERR wrong number of arguments for 'lpop' command")
        key = args[0]
        
        self._expire_if_needed(key)
        type_error = self._check_type(key, list)
        if type_error:
            return type_error
        
        if key not in self.data or len(self.data[key]) == 0:
            return ("bult", None)
        
        value = self.data[key].pop(0)
        if len(self.data[key]) == 0:
            del self.data[key]
            
        return ("bulk", value)
    
    def cmd_rpop(self, args):
        if len(args) != 1:
            return ("error", "ERR wrong number of arguments for 'rpop' command")
        key = args[0]

        self._expire_if_needed(key)
        type_error = self._check_type(key, list)
        if type_error:
            return type_error

        if key not in self.data or len(self.data[key]) == 0:
            return ("bulk", None)

        value = self.data[key].pop()
        if len(self.data[key]) == 0:
            del self.data[key]

        return ("bulk", value)

    def cmd_lrange(self, args):
        if len(args) != 3:
            return ("error", "ERR wrong number of arguments for 'lrange' command")
        key, start, stop = args

        self._expire_if_needed(key)
        type_error = self._check_type(key, list)
        if type_error:
            return type_error

        if key not in self.data:
            return ("array", [])

        try:
            start, stop = int(start), int(stop)
        except ValueError:
            return ("error", "ERR value is not an integer or out of range")

        lst = self.data[key]
        # Redis LRANGE is inclusive on both ends, Python slicing is exclusive on stop
        if stop == -1:
            result = lst[start:]
        else:
            result = lst[start:stop + 1]

        return ("array", result)