import datetime
import select
import socket
import sys
import threading
import time
import typing

SOCKET_CONNECTION_TIMEOUT_SECONDS = 10
SOCKET_OPERATION_TIMEOUT_SECONDS = 0.1
SELECT_TIMEOUT_SECONDS = 0.1
PACKET_LENGTH_BYTES = 128
HALTED = False

def make_header(name: typing.Union[None, str] = None) -> str:
    '''
    Every message printed to the console has a header
    containing the message sender and the sending time.
    '''
    if name is None:
        name = 'system'
    else:
        name = f'[{name}]'
    time_str = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')
    return f'({name} {time_str}) '

def make_packet(data: bytes) -> bytes:
    '''
    Packets are truncated/padded to a fixed-size.
    '''
    global PACKET_LENGTH_BYTES
    if len(data) > PACKET_LENGTH_BYTES:
        return data[:PACKET_LENGTH_BYTES]
    else:
        return data + (b' ' * (PACKET_LENGTH_BYTES - len(data)))

class Neighbor:
    '''
    Each neighbor object contains:
    (1) a read buffer containing data received from the corresponding neighbor node,
    (2) a write buffer containing data to be sent to the corresponding neighbor node.
    '''
    def __init__(self, so: socket.socket, remote_addr: tuple[str, int],
                 read_buffer: bytes, write_buffer: bytes):
        self.so = so
        self.remote_addr = remote_addr
        self.read_buffer = read_buffer
        self.write_buffer = write_buffer

    def __str__(self):
        return (f'Neighbor {id(self.so)} {self.so.getsockname()} {self.remote_addr} ' +
                f'{self.read_buffer} {self.write_buffer}')

def listener(lock: threading.Lock, server_socket: socket.socket,
             neighbors: list[Neighbor]) -> None:
    global HALTED
    round_ctr = 0
    accept_ctr = 0
    while True:
        round_ctr += 1
        # check the halting condition
        with lock:
            if HALTED:
                sys.stderr.write(make_header() +
                                 f' listener rounds = {round_ctr}' +
                                 f' listener accepts = {accept_ctr}\n')
                return
        # try to accept new connections
        try:
            client_socket, client_addr = server_socket.accept()
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
            with lock:
                neighbors.append(Neighbor(client_socket, client_addr, b'', b''))
                sys.stderr.write(make_header() +
                                 f'accepted a new connection from {client_addr}\n')
            accept_ctr += 1
        except TimeoutError:
            pass

def relayer(lock: threading.Lock, neighbors: list[Neighbor]) -> None:
    global PACKET_LENGTH_BYTES, HALTED
    round_ctr = 0
    read_ctr = 0
    write_ctr = 0
    while True:
        round_ctr += 1
        # avoid busy waiting
        time.sleep(SOCKET_OPERATION_TIMEOUT_SECONDS)
        # check the halting condition
        with lock:
            if HALTED:
                sys.stderr.write(make_header() +
                                 f' relayer rounds = {round_ctr}' +
                                 f' relayer read bytes = {read_ctr}' +
                                 f' relayer write bytes = {write_ctr}\n')
                return
        # obtain a list of current sockets
        # note: the listener may add new neighbor objects to "neighbors"
        # during this round of relay
        with lock:
            so_list = [neighbor.so for neighbor in neighbors]
        if so_list:
            readable_so_list, writable_so_list, exceptional_so_list = select.select(
                so_list, so_list, so_list, SELECT_TIMEOUT_SECONDS)
        else:
            continue
        # read and detect dead sockets
        dead_so_list = []
        reads = {}
        for so in readable_so_list:
            data = so.recv(PACKET_LENGTH_BYTES)
            if data == b'':
                dead_so_list.append(so)
            else:
                reads[id(so)] = data
                read_ctr += len(data)
        # save reads to buffers, print whole packets, move printed packets to relay buffers
        with lock:
            for neighbor in neighbors:
                sid = id(neighbor.so)
                if sid in reads:
                    neighbor.read_buffer += reads[sid]
                if len(neighbor.read_buffer) >= PACKET_LENGTH_BYTES:
                    packet = neighbor.read_buffer[:PACKET_LENGTH_BYTES]
                    neighbor.read_buffer = neighbor.read_buffer[PACKET_LENGTH_BYTES:]
                    print(packet.decode().strip())
                    for other in neighbors:
                        if id(other.so) != sid:
                            other.write_buffer += packet
        # get writable data
        writes = {}
        with lock:
            for neighbor in neighbors:
                sid = id(neighbor.so)
                if neighbor.write_buffer:
                    writes[sid] = neighbor.write_buffer
                    neighbor.write_buffer = b''
        # try to write everything
        for so in writable_so_list:
            sid = id(so)
            if sid in writes:
                sent = so.send(writes[sid])
                writes[sid] = writes[sid][sent:]
                write_ctr += sent
        # store back not-written parts
        with lock:
            for neighbor in neighbors:
                sid = id(neighbor.so)
                if sid in writes:
                    neighbor.write_buffer = writes[sid] + neighbor.write_buffer
        # detect disconnections and update the neighbor list
        dead_sids = set([id(so) for so in dead_so_list] +
                        [id(so) for so in exceptional_so_list])
        with lock:
            remaining_neighbors = []
            for neighbor in neighbors:
                if id(neighbor.so) in dead_sids:
                    sys.stderr.write(make_header() +
                                     f'detected the disconnection of {neighbor.remote_addr}\n')
                else:
                    remaining_neighbors.append(neighbor)
            neighbors.clear()
            neighbors.extend(remaining_neighbors)

def start_node(name: str, my_addr: tuple[str, int],
               inviter_addr: typing.Union[None, tuple[str, int]]) -> None:
    global HALTED
    neighbors = []  # shared between all three threads of this node
    # try to connect to the inviter (if there is one)
    if inviter_addr:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(SOCKET_CONNECTION_TIMEOUT_SECONDS)
        try:
            client_socket.connect(inviter_addr)
        except socket.timeout:
            sys.exit(make_header() + f'connection to the inviter ({inviter_addr}) timed out')
        sys.stderr.write(make_header() + f'connected to the inviter ({inviter_addr})\n')
        client_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
        neighbors.append(Neighbor(client_socket, inviter_addr, b'', b''))
    # start the current node's server part
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
    server_socket.bind(my_addr)
    server_socket.listen()  # this does not need to block even if "setblocking(True)"
    lock = threading.Lock()
    listener_thread = threading.Thread(target = listener, args = (lock, server_socket, neighbors))
    listener_thread.start()
    relayer_thread = threading.Thread(target = relayer, args = (lock, neighbors))
    relayer_thread.start()
    # start handling user inputs
    while True:
        content = input()
        if content == '':
            # set the halting condition
            with lock:
                HALTED = True
            # wait for the other two threads
            listener_thread.join()
            relayer_thread.join()
            return
        else:
            message = make_header(name) + content
            data = make_packet(message.encode())
            with lock:
                print(message)
                for neighbor in neighbors:
                    neighbor.write_buffer += data  # send data to all neighbor nodes

if __name__ == '__main__':
    if (len(sys.argv) != 4) and (len(sys.argv) != 6):
        sys.exit(make_header() +
                 f'python3 {sys.argv[0]} <name> <my-ip> <my-port> [inviter-ip] [inviter-port]')
    name = sys.argv[1]
    my_addr = (sys.argv[2], int(sys.argv[3]))
    inviter_addr = None if len(sys.argv) == 4 else (sys.argv[4], int(sys.argv[5]))
    start_node(name, my_addr, inviter_addr)
