import sys
import subprocess
import time

class P2PTreeTestError(Exception):
    pass

def launch(config: list[str]) -> subprocess.Popen:
    return subprocess.Popen(args = ['python3', 'src/node.py'] + config,
                            stdin = subprocess.PIPE,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE,
                            text = True)

def write_line(p: subprocess.Popen, s: str) -> None:
    p.stdin.write(s + '\n')
    p.stdin.flush()

def verify_out_line(p: subprocess.Popen, s: str) -> None:
    if s not in p.stdout.readline():
        raise P2PTreeTestError()

def verify_err_line(p: subprocess.Popen, s: str) -> None:
    if s not in p.stderr.readline():
        raise P2PTreeTestError()

def nap() -> None:
    time.sleep(1)

def p2p_tree_test_one_node() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '8001'])
        nap()
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        write_line(a, '')
        nap()
        if a.poll() is None:
            a.kill()
            raise P2PTreeTestError()
        return True
    except P2PTreeTestError:
        return False

def p2p_tree_test_two_nodes() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '8001'])
        nap()
        b = launch(['B', '127.0.0.1', '8002', '127.0.0.1', '8001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        verify_out_line(b, 'This is A')
        write_line(b, 'This is B')
        verify_out_line(a, 'This is B')
        verify_out_line(b, 'This is B')
        write_line(b, '')
        verify_err_line(a, 'detected')
        nap()
        if b.poll() is None:
            b.kill()
            raise P2PTreeTestError()
        write_line(a, '')
        nap()
        if a.poll() is None:
            a.kill()
            raise P2PTreeTestError()
        return True
    except P2PTreeTestError:
        return False

if __name__ == '__main__':
    sys.exit('This is a script to test the previous CLI version of p2p-tree.')
    global_dict = globals().copy()
    for k, v in global_dict.items():
        if k.startswith('p2p_tree_test'):
            if v():
                print(f'test {k} passed')
            else:
                sys.exit(f'test {k} failed')
