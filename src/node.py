import datetime
import select
import socket
import sys
import threading

DATA_LENGTH = 128

def pad_data(data: bytes, data_length: int) -> bytes:
    if len(data) > data_length:
        return data[:data_length]
    else:
        return data + (b' ' * (data_length - len(data)))

def send_data(client_socket: socket.socket, data: bytes) -> None:
    data_length = len(data)
    sent = 0
    while sent < data_length:
        sent += client_socket.send(data[sent:])

def receive_data(client_socket: socket.socket,
                 data_length: int) -> bytes:
    data = b''
    while len(data) < data_length:
        data += client_socket.recv(data_length - len(data))
    return data

def listener(lock: threading.Lock, server_socket: socket.socket,
             neighbor_sockets: list[socket.socket]) -> None:
    server_socket.listen(5)
    while True:
        client_socket, _ = server_socket.accept()
        with lock:
            neighbor_sockets.append(client_socket)
            sys.stderr.write('* Accepted a new connection\n')

def relayer(lock: threading.Lock,
            neighbor_sockets: list[socket.socket]) -> None:
    while True:
        with lock:
            if neighbor_sockets:
                ready_to_read, _, __ = select.select(neighbor_sockets,
                                                 [], [], 0)
                if ready_to_read:
                    for source_socket in ready_to_read:
                        data = receive_data(source_socket, DATA_LENGTH)
                        sys.stderr.write('* Received data\n')
                        message = data.decode().strip()
                        print(message)
                        for neighbor_socket in neighbor_sockets:
                            if (source_socket.getsockname()
                                != neighbor_socket.getsockname()):
                                send_data(neighbor_socket, data)
                        sys.stderr.write('* Relayed data\n')

def start_node(name: str, my_addr: tuple[str, int],
               inviter_addr: tuple[str, int]) -> None:
    lock = threading.Lock()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(my_addr)
    neighbor_sockets = []
    if inviter_addr[0] != 'start':
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(inviter_addr)
        sys.stderr.write('* Connected to the inviter\n')
        neighbor_sockets.append(client_socket)
    threading.Thread(target = listener,
                     args = (lock, server_socket, neighbor_sockets)).start()
    threading.Thread(target = relayer,
                     args = (lock, neighbor_sockets)).start()
    while True:
        content = input()
        utctime = datetime.datetime.utcnow()
        message = f'[{name} sent at {utctime} (UTC)]: {content}'
        data = pad_data(message.encode(), DATA_LENGTH)
        with lock:
            print(message)
            for neighbor_socket in neighbor_sockets:
                send_data(neighbor_socket, data)
            sys.stderr.write('* Sent data\n')

if __name__ == '__main__':
    if len(sys.argv) != 6:
        sys.exit(f'Usage: python3 {sys.argv[0]}'
                  ' <name> <my-ip> <my-port> <inviter-ip> <inviter-port>')
    start_node(sys.argv[1], (sys.argv[2], int(sys.argv[3])),
                            (sys.argv[4], int(sys.argv[5])))
