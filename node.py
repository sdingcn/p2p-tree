import datetime
import select
import socket
import sys
import threading
import time
try:
    import tkinter
    import tkinter.scrolledtext
    import tkinter.ttk
except ModuleNotFoundError:
    pass
import typing

# TODO: reduce the number of global variables
SOCKET_CONNECTION_TIMEOUT_SECONDS = 10
SOCKET_OPERATION_TIMEOUT_SECONDS = 0.1
SELECT_TIMEOUT_SECONDS = 0.1
PACKET_LENGTH_BYTES = 128
HALTED = False

def make_header(name: typing.Union[None, str] = None) -> str:
    '''
    sender and time
    '''
    name = 'system' if name is None else f'[{name}]'
    time_string = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')
    return f'({name} {time_string}) '

def dump_to_stderr(message: str) -> None:
    sys.stderr.write(message)
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
    All buffers append new data to the right end.
    '''
    def __init__(self, the_socket: socket.socket, remote_address: tuple[str, int],
                 read_buffer: bytes, write_buffer: bytes):
        self.the_socket = the_socket
        self.remote_address = remote_address
        self.read_buffer = read_buffer
        self.write_buffer = write_buffer

    def __str__(self):
        return (f'Neighbor {id(self.the_socket)} {self.the_socket.getsockname()} '
                f'{self.remote_address} {self.read_buffer} {self.write_buffer}')

def listener_core(lock: threading.Lock, server_socket: socket.socket,
                  neighbors: list[Neighbor]) -> None:
    global HALTED
    round_counter = 0
    accept_counter = 0
    while True:
        # check the halting condition
        with lock:
            if HALTED:
                dump_to_stderr(make_header() + f' listener rounds = {round_counter}' +
                               f' listener accepts = {accept_counter}\n')
                return
        # try to accept new connections
        try:
            client_socket, client_address = server_socket.accept()
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
            with lock:
                neighbors.append(Neighbor(client_socket, client_address, b'', b''))
                dump_to_stderr(make_header() +
                               f'accepted a new connection from {client_address}\n')
            accept_counter += 1
        except TimeoutError:
            pass
        # round counter update
        round_counter += 1

def listener(lock: threading.Lock, server_socket: socket.socket,
             neighbors: list[Neighbor]) -> None:
    global HALTED
    try:
        listener_core(lock, server_socket, neighbors)
    except:  # when one thread throws exceptions, let all other threads terminate through HALTED
        with lock:
            HALTED = True

def relayer_core(lock: threading.Lock, neighbors: list[Neighbor],
                 output: typing.Callable[[str], None]) -> None:
    global PACKET_LENGTH_BYTES, HALTED
    round_counter = 0
    read_counter = 0
    write_counter = 0
    while True:
        # avoid busy waiting
        time.sleep(SOCKET_OPERATION_TIMEOUT_SECONDS)
        # check the halting condition
        with lock:
            if HALTED:
                dump_to_stderr(make_header() + f' relayer rounds = {round_counter}' +
                               f' relayer read bytes = {read_counter}' +
                               f' relayer write bytes = {write_counter}\n')
                return
        # freeze and obtain a list of current sockets
        # note: the listener may add new neighbor objects to "neighbors"
        # during this round of relayer
        with lock:
            socket_list = [neighbor.the_socket for neighbor in neighbors]
        if socket_list:
            readable_socket_list, writable_socket_list, exceptional_socket_list = select.select(
                socket_list, socket_list, socket_list, SELECT_TIMEOUT_SECONDS)
        else:
            continue
        # prepare variables
        reads = {}
        writes = {}
        writable_socket_id_set = set([id(the_socket) for the_socket in writable_socket_list])
        # read data and detect dead sockets
        dead_socket_list = []
        for the_socket in readable_socket_list:
            data = the_socket.recv(PACKET_LENGTH_BYTES)
            if data == b'':
                dead_socket_list.append(the_socket)
            else:
                reads[id(the_socket)] = data
                read_counter += len(data)
        # save reads to buffers, print whole packets, relay printed packets, collect writes
        with lock:
            for neighbor in neighbors:
                socket_id = id(neighbor.the_socket)
                if socket_id in reads:
                    neighbor.read_buffer += reads[socket_id]
                if len(neighbor.read_buffer) >= PACKET_LENGTH_BYTES:
                    packet = neighbor.read_buffer[:PACKET_LENGTH_BYTES]
                    neighbor.read_buffer = neighbor.read_buffer[PACKET_LENGTH_BYTES:]
                    message = packet.decode().strip() + '\n'
                    output(message)
                    for other in neighbors:
                        if id(other.the_socket) != socket_id:  # to be sent to "other" neighbors
                            other.write_buffer += packet
            for neighbor in neighbors:
                socket_id = id(neighbor.the_socket)
                if (socket_id in writable_socket_id_set) and neighbor.write_buffer:
                    writes[socket_id] = neighbor.write_buffer
                    neighbor.write_buffer = b''
        # write data
        for the_socket in writable_socket_list:
            socket_id = id(the_socket)
            if socket_id in writes:
                sent = the_socket.send(writes[socket_id])
                writes[socket_id] = writes[socket_id][sent:]
                write_counter += sent
        # store back not-written parts
        with lock:
            for neighbor in neighbors:
                socket_id = id(neighbor.the_socket)
                if socket_id in writes:
                    # prepend the old data to the beginning
                    neighbor.write_buffer = writes[socket_id] + neighbor.write_buffer
        # detect disconnections and update the neighbor list
        dead_socket_id_set = set([id(the_socket) for the_socket in dead_socket_list] +
                                 [id(the_socket) for the_socket in exceptional_socket_list])
        with lock:
            remaining_neighbors = []
            for neighbor in neighbors:
                if id(neighbor.the_socket) in dead_socket_id_set:
                    dump_to_stderr(make_header() +
                                   f'detected the disconnection of {neighbor.remote_address}\n')
                else:
                    remaining_neighbors.append(neighbor)
            neighbors.clear()
            neighbors.extend(remaining_neighbors)  # cannot use '=' because that's re-binding
        # round counter update
        round_counter += 1

def relayer(lock: threading.Lock, neighbors: list[Neighbor],
            output: typing.Callable[[str], None]) -> None:
    global HALTED
    try:
        relayer_core(lock, neighbors, output)
    except:  # when one thread throws exceptions, let all other threads terminate through HALTED
        with lock:
            HALTED = True

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
    root.rowconfigure(0, weight = 1)
    root.columnconfigure(0, weight = 1)
    frame = tkinter.ttk.Frame(root, padding = 5, borderwidth = 5, relief = 'ridge')
    frame.grid(row = 0, column = 0, padx = 5, pady = 5)
    frame.rowconfigure(0, weight = 1)
    frame.rowconfigure(1, weight = 1)
    frame.columnconfigure(0, weight = 1)
    display_area = tkinter.scrolledtext.ScrolledText(frame)
    display_area.bind('<Key>', lambda e: 'break')
    display_area.grid(row = 0, column = 0, sticky = 'NSEW')
    entry_variable = tkinter.StringVar()
    entry_area = tkinter.Entry(frame, textvariable = entry_variable, borderwidth = 3,
                               relief = 'ridge')
    entry_area.grid(row = 1, column = 0, sticky = 'NSEW')

    def gui_output(message: str) -> None:
        nonlocal display_area
        display_area.insert(tkinter.INSERT, message)

    def handle_input(event: tkinter.Event) -> None:
        nonlocal name, neighbors, lock, display_area, entry_variable
        entry_text = entry_variable.get()
        entry_variable.set('')
        message = make_header(name) + entry_text + '\n'
        data = make_packet(message.encode())
        with lock:
            gui_output(message)
            for neighbor in neighbors:
                neighbor.write_buffer += data  # append data to all neighbor nodes' buffers

    entry_area.bind('<Key-Return>', handle_input)
    # start the relayer
    relayer_thread = threading.Thread(target = relayer, args = (lock, neighbors, gui_output))
    relayer_thread.start()

    def exit_loop() -> None:
        nonlocal lock, listener_thread, root, relayer_thread
        stop_and_wait(lock, listener_thread, relayer_thread)
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', exit_loop)
    entry_area.focus_set()
    root.mainloop()

def cli_loop(name: str, neighbors: list[Neighbor], lock: threading.Lock,
             listener_thread: typing.Union[None, threading.Thread]) -> None:

    def cli_output(message: str) -> None:
        sys.stdout.write(message)
        sys.stdout.flush()

    # start the relayer
    relayer_thread = threading.Thread(target = relayer, args = (lock, neighbors, cli_output))
    relayer_thread.start()
    while True:
        line = input()
        if line == '':
            stop_and_wait(lock, listener_thread, relayer_thread)
            return
        else:
            message = make_header(name) + line + '\n'
            data = make_packet(message.encode())
            with lock:
                cli_output(message)
                for neighbor in neighbors:
                    neighbor.write_buffer += data  # send data to all neighbor nodes

def start_node(name: str, my_address: tuple[str, int],
               inviter_address: typing.Union[None, tuple[str, int]], option: str) -> None:
    # prepare the neighbor list to be shared by all threads of this node
    neighbors = []
    # try to connect to the inviter
    if inviter_address:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.settimeout(SOCKET_CONNECTION_TIMEOUT_SECONDS)
        try:
            client_socket.connect(inviter_address)
        except socket.timeout:
            sys.exit(make_header() + f'connection to the inviter ({inviter_address}) timed out')
        dump_to_stderr(make_header() + f'connected to the inviter ({inviter_address})\n')
        client_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
        neighbors.append(Neighbor(client_socket, inviter_address, b'', b''))
    # start the listener
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(SOCKET_OPERATION_TIMEOUT_SECONDS)
    server_socket.bind(my_address)
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
    my_address = (sys.argv[3], int(sys.argv[4]))
    inviter_address = None if len(sys.argv) == 5 else (sys.argv[5], int(sys.argv[6]))
    try:
        start_node(name, my_address, inviter_address, option)
    except:  # when one thread throws exceptions, let all other threads terminate through HALTED
        with lock:
            HALTED = True
