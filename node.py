import datetime
import select
import socket
import sys
import threading
import time
import tkinter
import tkinter.scrolledtext
import tkinter.ttk
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

def dump_to_stderr(s: str) -> None:
    sys.stderr.write(make_header() + s)
    sys.stderr.flush()

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
                dump_to_stderr(f' listener rounds = {round_ctr}'
                               f' listener accepts = {accept_ctr}\n')
                return
        # try to accept new connections
        try:
            client_socket, client_addr = server_socket.accept()
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
            with lock:
                neighbors.append(Neighbor(client_socket, client_addr, b'', b''))
                dump_to_stderr(f'accepted a new connection from {client_addr}\n')
            accept_ctr += 1
        except TimeoutError:
            pass

def relayer(lock: threading.Lock, neighbors: list[Neighbor],
            output: typing.Callable[[str], None]) -> None:
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
                dump_to_stderr(f' relayer rounds = {round_ctr}'
                               f' relayer read bytes = {read_ctr}'
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
                    output(packet.decode().strip() + '\n')
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
                    dump_to_stderr(f'detected the disconnection of {neighbor.remote_addr}\n')
                else:
                    remaining_neighbors.append(neighbor)
            neighbors.clear()
            neighbors.extend(remaining_neighbors)

def stop_and_wait(lock: threading.Lock,
                 listener_thread: typing.Union[None, threading.Thread],
                 relayer_thread: typing.Union[None, threading.Thread]) -> None:
    global HALTED
    with lock:
        HALTED = True
    if listener_thread:
        listener_thread.join()
    if relayer_thread:
        relayer_thread.join()

def gui_loop(name: str, neighbors: list[Neighbor], lock: threading.Lock,
             listener_thread: typing.Union[None, threading.Thread]) -> None:
    root = tkinter.Tk()
    root.title('p2p-tree')
    root.resizable(False, False)
    # root.attributes('-alpha', 0.8)
    root.rowconfigure(0, weight = 1)
    root.columnconfigure(0, weight = 1)
    frm = tkinter.ttk.Frame(root, padding = 5, borderwidth = 5, relief = 'ridge')
    frm.grid(row = 0, column = 0, padx = 5, pady = 5)
    frm.rowconfigure(0, weight = 1)
    frm.rowconfigure(1, weight = 1)
    frm.columnconfigure(0, weight = 1)
    display_area = tkinter.scrolledtext.ScrolledText(frm)
    display_area.bind('<Key>', lambda e: 'break')
    display_area.grid(row = 0, column = 0, sticky = 'NSEW')
    entry_variable = tkinter.StringVar()
    entry_area = tkinter.Entry(frm, textvariable = entry_variable, borderwidth = 3,
                               relief = 'ridge')
    entry_area.grid(row = 1, column = 0, sticky = 'NSEW')

    def handle_input(event: tkinter.Event) -> None:
        nonlocal display_area, entry_variable, name, neighbors, lock
        entry_text = entry_variable.get()
        entry_variable.set('')
        message = make_header(name) + entry_text
        data = make_packet(message.encode())
        with lock:
            display_area.insert(tkinter.INSERT, message + '\n')
            for neighbor in neighbors:
                neighbor.write_buffer += data  # append data to all neighbor nodes' buffers

    entry_area.bind('<Key-Return>', handle_input)

    def gui_output(s: str) -> None:
        nonlocal display_area
        display_area.insert(tkinter.INSERT, s)

    # start the current node's relayer part
    relayer_thread = threading.Thread(target = relayer, args = (lock, neighbors, gui_output))
    relayer_thread.start()

    def exit_loop() -> None:
        nonlocal lock, listener_thread, relayer_thread, root
        stop_and_wait(lock, listener_thread, relayer_thread)
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', exit_loop)
    entry_area.focus_set()
    root.mainloop()

def cli_loop(name: str, neighbors: list[Neighbor], lock: threading.Lock,
             listener_thread: typing.Union[None, threading.Thread]) -> None:

    def cli_output(s: str) -> None:
        sys.stdout.write(s)
        sys.stdout.flush()

    # start the current node's relayer part
    relayer_thread = threading.Thread(target = relayer, args = (lock, neighbors, cli_output))
    relayer_thread.start()
    while True:
        content = input()
        if content == '':
            stop_and_wait(lock, listener_thread, relayer_thread)
            return
        else:
            message = make_header(name) + content
            data = make_packet(message.encode())
            with lock:
                sys.stdout.write(message + '\n')
                sys.stdout.flush()
                for neighbor in neighbors:
                    neighbor.write_buffer += data  # send data to all neighbor nodes

def start_node(name: str, my_addr: tuple[str, int],
               inviter_addr: typing.Union[None, tuple[str, int]], option: str) -> None:
    # prepare the neighbor list to be shared by all threads of this node
    neighbors = []
    # try to connect to the inviter
    if inviter_addr:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(SOCKET_CONNECTION_TIMEOUT_SECONDS)
        try:
            client_socket.connect(inviter_addr)
        except socket.timeout:
            sys.exit(make_header() + f'connection to the inviter ({inviter_addr}) timed out')
        dump_to_stderr(f'connected to the inviter ({inviter_addr})\n')
        client_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
        neighbors.append(Neighbor(client_socket, inviter_addr, b'', b''))
    # start the current node's listener part
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
    server_socket.bind(my_addr)
    server_socket.listen()  # this does not need to block even if "setblocking(True)"
    lock = threading.Lock()
    listener_thread = threading.Thread(target = listener, args = (lock, server_socket, neighbors))
    listener_thread.start()
    # start the main loop based on the option (GUI/CLI)
    if option == 'gui':
        gui_loop(name, neighbors, lock, listener_thread)
    elif option == 'cli':
        cli_loop(name, neighbors, lock, listener_thread)
    else:
        stop_and_wait(lock, listener_thread, None)
        sys.exit(make_header() + f'unknown or corrupted option "{option}"')

if __name__ == '__main__':
    if (len(sys.argv) != 5) and (len(sys.argv) != 7):
        sys.exit(
            f'python3 {sys.argv[0]} '
            '<gui/cli> <name> <my-ip> <my-port> [inviter-ip] [inviter-port]'
        )
    # TODO: add some argument checks
    option = sys.argv[1]
    name = sys.argv[2]
    my_addr = (sys.argv[3], int(sys.argv[4]))
    inviter_addr = None if len(sys.argv) == 5 else (sys.argv[5], int(sys.argv[6]))
    start_node(name, my_addr, inviter_addr, option)
