import socket
import threading
import sys

class Node:

    def __init__(self, name: str, my_addr: tuple[str, int], neighbor_addr_list: list[tuple[str, int]]):
        self.name = name
        self.my_addr = my_addr
        self.neighbor_addr_list = neighbor_addr_list

def receiver(lock: threading.Lock, skt: socket.socket, node: Node) -> None:
    while True:
        # 64 KiB buffer
        data, addr = skt.recvfrom(64 * 1024)
        packet = data.decode()
        header, content = packet[0], packet[1:]
        # connection packet
        if header == 'C':
            with lock:
                node.neighbor_addr_list.append(addr)
        # message packet
        elif header == 'M':
            with lock:
                print(content)
                for neighbor_addr in node.neighbor_addr_list:
                    if neighbor_addr != addr:
                        skt.sendto(('M' + content).encode(), neighbor_addr)
        # unrecognized packet
        else:
            pass

def start_node(name: str, my_addr: tuple[str, int], inviter_addr: tuple[str, int]) -> None:
    lock = threading.Lock()
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.bind(my_addr)
    if inviter_addr[0] == 'start':
        node = Node(name, my_addr, [])
    else:
        node = Node(name, my_addr, [inviter_addr])
        skt.sendto('C'.encode(), inviter_addr)
    threading.Thread(target = receiver, args = (lock, skt, node)).start()
    while True:
        message = input()
        with lock:
            named_message = f'[Message from {name}] ' + message
            print(named_message)
            for neighbor_addr in node.neighbor_addr_list:
                skt.sendto(('M' + named_message).encode(), neighbor_addr)

if __name__ == '__main__':
    if len(sys.argv) != 6:
        sys.exit(f'Usage: python3 {sys.argv[0]} <name> <my-ip> <my-port> <inviter-ip> <inviter-port>')
    start_node(sys.argv[1], (sys.argv[2], int(sys.argv[3])), (sys.argv[4], int(sys.argv[5])))
