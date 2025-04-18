import sys
import subprocess
import time

SUBPROCESS_LIST = []

def clean() -> None:
    global SUBPROCESS_LIST
    for p in SUBPROCESS_LIST:
        p.kill()

class P2PTreeTestError(Exception):
    pass

def launch(config: list[str]) -> subprocess.Popen:
    global SUBPROCESS_LIST
    p = subprocess.Popen(args = ['python3', 'node.py', 'cli'] + config,
                         stdin = subprocess.PIPE,
                         stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE,
                         text = True)
    if p.poll():
        raise P2PTreeTestError()
    SUBPROCESS_LIST.append(p)
    return p

def write_line(p: subprocess.Popen, s: str) -> None:
    p.stdin.write(s + '\n')
    p.stdin.flush()

def verify_out_line(p: subprocess.Popen, s: str) -> None:
    print('.', end = '', flush = True)
    if s not in p.stdout.readline():
        raise P2PTreeTestError()

def verify_err_line(p: subprocess.Popen, s: str) -> None:
    print('.', end = '', flush = True)
    if s not in p.stderr.readline():
        raise P2PTreeTestError()

def verify_termination(p: subprocess.Popen) -> None:
    print('.', end = '', flush = True)
    if p.poll() is None:
        p.kill()
        raise P2PTreeTestError()

def nap() -> None:
    time.sleep(1)

def p2p_tree_test_1() -> None:
    try:
        a = launch(['A', 'localhost', '10001'])
        nap()
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        write_line(a, '')
        nap()
        verify_termination(a)
    except P2PTreeTestError:
        clean()
        raise

def p2p_tree_test_2() -> None:
    try:
        a = launch(['A', 'localhost', '10001'])
        nap()
        b = launch(['B', 'localhost', '10002', 'localhost', '10001'])
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
        verify_termination(b)
        write_line(a, '')
        nap()
        verify_termination(a)
    except P2PTreeTestError:
        clean()
        raise

def p2p_tree_test_3() -> None:
    try:
        a = launch(['A', 'localhost', '10001'])
        nap()
        b = launch(['B', 'localhost', '10002', 'localhost', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        c = launch(['C', 'localhost', '10003', 'localhost', '10002'])
        nap()
        verify_err_line(b, 'accepted')
        verify_err_line(c, 'connected')
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        verify_out_line(b, 'This is A')
        verify_out_line(c, 'This is A')
        write_line(b, 'This is B')
        verify_out_line(a, 'This is B')
        verify_out_line(b, 'This is B')
        verify_out_line(c, 'This is B')
        write_line(c, 'This is C')
        verify_out_line(a, 'This is C')
        verify_out_line(b, 'This is C')
        verify_out_line(c, 'This is C')
        write_line(b, '')
        verify_err_line(a, 'detected')
        verify_err_line(c, 'detected')
        nap()
        verify_termination(b)
        write_line(a, '')
        nap()
        verify_termination(a)
        write_line(c, '')
        nap()
        verify_termination(c)
    except P2PTreeTestError:
        clean()
        raise

def p2p_tree_test_4() -> None:
    try:
        a = launch(['A', 'localhost', '10001'])
        nap()
        b = launch(['B', 'localhost', '10002', 'localhost', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        c = launch(['C', 'localhost', '10003', 'localhost', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(c, 'connected')
        d = launch(['D', 'localhost', '10004', 'localhost', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(d, 'connected')
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        verify_out_line(b, 'This is A')
        verify_out_line(c, 'This is A')
        verify_out_line(d, 'This is A')
        write_line(b, 'This is B')
        verify_out_line(a, 'This is B')
        verify_out_line(b, 'This is B')
        verify_out_line(c, 'This is B')
        verify_out_line(d, 'This is B')
        write_line(c, 'This is C')
        verify_out_line(a, 'This is C')
        verify_out_line(b, 'This is C')
        verify_out_line(c, 'This is C')
        verify_out_line(d, 'This is C')
        write_line(d, 'This is D')
        verify_out_line(a, 'This is D')
        verify_out_line(b, 'This is D')
        verify_out_line(c, 'This is D')
        verify_out_line(d, 'This is D')
        write_line(b, '')
        verify_err_line(a, 'detected')
        write_line(c, '')
        verify_err_line(a, 'detected')
        write_line(d, '')
        verify_err_line(a, 'detected')
        nap()
        verify_termination(b)
        verify_termination(c)
        verify_termination(d)
        write_line(a, '')
        nap()
        verify_termination(a)
    except P2PTreeTestError:
        clean()
        raise

def p2p_tree_test_5() -> None:
    try:
        a = launch(['A', 'localhost', '10001'])
        nap()
        b = launch(['B', 'localhost', '10002', 'localhost', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        c = launch(['C', 'localhost', '10003', 'localhost', '10002'])
        nap()
        verify_err_line(b, 'accepted')
        verify_err_line(c, 'connected')
        d = launch(['D', 'localhost', '10004', 'localhost', '10003'])
        nap()
        verify_err_line(c, 'accepted')
        verify_err_line(d, 'connected')
        e = launch(['E', 'localhost', '10005', 'localhost', '10004'])
        nap()
        verify_err_line(d, 'accepted')
        verify_err_line(e, 'connected')
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        verify_out_line(b, 'This is A')
        verify_out_line(c, 'This is A')
        verify_out_line(d, 'This is A')
        verify_out_line(e, 'This is A')
        write_line(e, 'This is E')
        verify_out_line(a, 'This is E')
        verify_out_line(b, 'This is E')
        verify_out_line(c, 'This is E')
        verify_out_line(d, 'This is E')
        verify_out_line(e, 'This is E')
        write_line(c, '')
        verify_err_line(b, 'detected')
        verify_err_line(d, 'detected')
        nap()
        verify_termination(c)
        write_line(a, 'This is A again')
        verify_out_line(a, 'This is A again')
        verify_out_line(b, 'This is A again')
        write_line(e, 'This is E again')
        verify_out_line(d, 'This is E again')
        verify_out_line(e, 'This is E again')
        write_line(a, '')
        verify_err_line(b, 'detected')
        nap()
        verify_termination(a)
        write_line(b, '')
        nap()
        verify_termination(b)
        write_line(e, '')
        verify_err_line(d, 'detected')
        nap()
        verify_termination(e)
        write_line(d, '')
        nap()
        verify_termination(d)
    except P2PTreeTestError:
        clean()
        raise

if __name__ == '__main__':
    global_dict = globals().copy()
    for k, v in global_dict.items():
        if k.startswith('p2p_tree_test'):
            print(f'running test {k} ', end = '', flush = True)
            v()
            print()
