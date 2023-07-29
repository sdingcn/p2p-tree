import datetime
import socket
import sys
import threading
import typing

DATA_LENGTH = 128
HALT = False

class Neighbor:

    def __init__(self, so: socket.socket,
                 read_buffer: bytes, write_buffer: bytes):
        self.so = so
        self.read_buffer = read_buffer
        self.write_buffer = write_buffer

def pad_data(data: bytes) -> bytes:
    global DATA_LENGTH
    if len(data) > DATA_LENGTH:
        return data[:DATA_LENGTH]
    else:
        return data + (b' ' * (DATA_LENGTH - len(data)))

def listener(lock: threading.Lock, server_socket: socket.socket,
             neighbors: list[Neighbor]) -> None:
    global HALT
    server_socket.listen()
    while True:
        with lock:
            if HALT:
                return
        try:
            client_socket, _ = server_socket.accept()
        except socket.timeout:
            continue
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(0.1)
        with lock:
            neighbors.append(Neighbor(client_socket, b'', b''))
            sys.stderr.write('* Accepted a new connection\n')

def relayer(lock: threading.Lock,
            neighbors: list[Neighbor]) -> None:
    global DATA_LENGTH, HALT
    while True:
        with lock:
            if HALT:
                return
        so_list = []
        with lock:
            for neighbor in neighbors:
                so_list.append(neighbor.so)
        new_reads = {}
        dead_addrs = []
        for so in so_list:
            addr = so.getsockname()
            try:
                data = so.recv(DATA_LENGTH)
                if data:
                    new_reads[addr] = data
                else:
                    dead_addrs.append(addr)
            except socket.timeout:
                pass
            except ConnectionError:
                dead_addrs.append(addr)
        writables = {}
        with lock:
            for neighbor in neighbors:
                addr = neighbor.so.getsockname()
                if addr in new_reads:
                    neighbor.read_buffer += new_reads[addr]
                if len(neighbor.read_buffer) >= DATA_LENGTH:
                    data = neighbor.read_buffer[:DATA_LENGTH]
                    neighbor.read_buffer = neighbor.read_buffer[
                                           DATA_LENGTH:]
                    message = data.decode().strip()
                    print(message)
                    for other in neighbors:
                        other_addr = other.so.getsockname()
                        if other_addr != addr:
                            other.write_buffer += data
            for neighbor in neighbors:
                addr = neighbor.so.getsockname()
                writables[addr] = neighbor.write_buffer
                neighbor.write_buffer = b''
        for so in so_list:
            addr = so.getsockname()
            if addr in writables:
                try:
                    sent = so.send(writables[addr])
                    writables[addr] = writables[addr][sent:]
                except socket.timeout:
                    pass
                except ConnectionError:
                    dead_addrs.append(addr)
        with lock:
            for neighbor in neighbors:
                addr = neighbor.so.getsockname()
                if addr in writables:
                    neighbor.write_buffer = (writables[addr]
                                             + neighbor.write_buffer)
            updated_neighbors = []
            for neighbor in neighbors:
                addr = neighbor.so.getsockname()
                if addr not in dead_addrs:
                    updated_neighbors.append(neighbor)
                else:
                    sys.stderr.write('* Detected a disconnection\n')
            neighbors.clear()
            for neighbor in updated_neighbors:
                neighbors.append(neighbor)

def start_node(name: str, my_addr: tuple[str, int],
               inviter_addr: typing.Union[None, tuple[str, int]]) -> None:
    global HALT
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(0.1)
    server_socket.bind(my_addr)
    neighbors = []
    if inviter_addr:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(5)
        try:
            client_socket.connect(inviter_addr)
        except socket.timeout:
            sys.exit('*** Connection to the inviter timed out')
        sys.stderr.write('* Connected to the inviter\n')
        client_socket.settimeout(0.1)
        neighbors.append(Neighbor(client_socket, b'', b''))
    lock = threading.Lock()
    listener_thread = threading.Thread(target = listener,
                      args = (lock, server_socket, neighbors))
    listener_thread.start()
    relayer_thread = threading.Thread(target = relayer,
                     args = (lock, neighbors))
    relayer_thread.start()
    while True:
        content = input()
        if content == '':
            with lock:
                HALT = True
            listener_thread.join()
            relayer_thread.join()
            return
        else:
            utctime = datetime.datetime.utcnow()
            message = f'[{name} ({utctime})]: {content}'
            data = pad_data(message.encode())
            with lock:
                print(message)
                for neighbor in neighbors:
                    neighbor.write_buffer += data

if __name__ == '__main__':
    if (len(sys.argv) != 4) and (len(sys.argv) != 6):
        sys.exit(f'*** Usage: python3 {sys.argv[0]}'
                  ' <name> <my-ip> <my-port> [inviter-ip] [inviter-port]')
    name = sys.argv[1]
    my_addr = (sys.argv[2], int(sys.argv[3]))
    inviter_addr = None if len(sys.argv) == 4 else (sys.argv[4],
                                                    int(sys.argv[5]))
    start_node(name, my_addr, inviter_addr)
