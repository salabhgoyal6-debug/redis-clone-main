import socket
import threading 
import time 

from resp import RESPParser, encode_simple_string, encode_bulk_string, encode_error, encode_integer, encode_array
from store import Store

import signal
import sys

HOST = "127.0.0.1" # local host only accept connection from this machine 
PORT = 6380 # not using 6379 to avoid clashing with a real redis if installed 



def main():
    #AF_INET= uses IPv4 and SOCK_STREAM= uses tcp
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"server listening on {HOST}:{PORT}")
    
    store = Store() # one store is shared across all client connections 
    store.start_active_expiry() 
    start_periodic_save(store, interval=10)
    
    def handle_shutdown(signum, frame):
        print("\nShutting down, saving data...")
        store.save()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_shutdown)   # catches Ctrl+C
    
    while True:
        conn, addr = server_socket.accept()
        print(f"connected by {addr}")
        thread = threading.Thread(target=handle_client, args=(conn, store), daemon=True)
        thread.start()
        
def handle_client(conn, store):
    parser = RESPParser(conn)
    with conn:
        while True:
            command = parser.parse_command()
            if command is None:
                break
            
            print(f"Parsed command: {command}")
            
            response_type, value = store.execute(command)
            conn.sendall(encode_response(response_type, value))


def start_periodic_save(store, interval):
    def saver():
        while True:
            time.sleep(interval)
            store.save()
    thread = threading.Thread(target=saver, daemon=True)
    thread.start()

def encode_response(response_type, value):
    if response_type == "simple":
        return encode_simple_string(value)
    elif response_type == "error":
        return encode_error(value)
    elif response_type == "integer":
        return encode_integer(value)
    elif response_type == "bulk":
        return encode_bulk_string(value)
    elif response_type == "array":
        return encode_array(value)
    
if __name__ == "__main__":
    main()