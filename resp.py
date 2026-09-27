class RESPParser:
    # creating a class whose only work is to to read and parse  resp message
    def __init__(self, sock):
        self.sock = sock # stores the client socket 
        self.buffer = b"" #tcp is a byte stream not a message stream
        
    def _read_line(self):
        "read lines until we hit \\r\n"
        while b"\r\n" not in self.buffer:
            chunk = self.sock.recv(1024)
            if not chunk :
                return None # it means client disconnected 
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\r\n", 1)
        return line 
    
    def _read_exact(self, n):
        while len(self.buffer) < n :
            chunk = self.sock.recv(1024)
            if not chunk:
                return None
            self.buffer += chunk 
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data 
    
    def parse_command(self):
        # read one full resp command means 9an array of bulk strings) and returns it as a python list of strings 
        line = self._read_line()
        if line is None:
            return None
        
        if not line.startswith(b"*"):
            return None
        num_elements = int(line[1:])
        command = []
        
        for _ in range(num_elements):
            bulk_header = self._read_line()
            length = int(bulk_header[1:])
            data = self._read_exact(length)
            self._read_exact(2)
            command.append(data.decode())
            
        return command 
    

def encode_simple_string(s):
    return f"+{s}\r\n".encode()

def encode_error(msg):
    return f"-{msg}\r\n".encode()

def encode_integer(n):
    return f":{n}\r\n".encode()

def encode_bulk_string(s):
    if s is None:
        return b"$-1\r\n"          # RESP's way of saying "nil"/null
    return f"${len(s)}\r\n{s}\r\n".encode()
        
def encode_array(items):
    if items is None:
        return b"*-1\r\n"   # nil array
    parts = [f"*{len(items)}\r\n".encode()]
    for item in items:
        parts.append(encode_bulk_string(item))
    return b"".join(parts)