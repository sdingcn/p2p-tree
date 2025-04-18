import sys
import subprocess
import time

class P2PTreeTestError(Exception):
    pass

def launch(config: list[str]) -> subprocess.Popen:
    return subprocess.Popen(args = ['python3', 'node.py', 'cli'] + config,
                            stdin = subprocess.PIPE,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE,
                            text = True)

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

def finalize(*ps: subprocess.Popen) -> None:
    sys.stderr.write(f'finalizing {len(ps)} processes...\n')
    for p in ps:
        if p.poll() is None:
            write_line(p, '')  # first ask the process to terminate
            nap()
            if p.poll() is None:  # if the process still doesn't terminate then kill it
                p.kill()

def p2p_tree_test_1() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '10001'])
        nap()
        write_line(a, 'This is A')
        verify_out_line(a, 'This is A')
        write_line(a, '')
        nap()
        verify_termination(a)
        return True
    except P2PTreeTestError:
        finalize(a)
        return False

def p2p_tree_test_2() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '10001'])
        nap()
        b = launch(['B', '127.0.0.1', '10002', '127.0.0.1', '10001'])
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
        return True
    except P2PTreeTestError:
        finalize(a, b)
        return False

def p2p_tree_test_3() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '10001'])
        nap()
        b = launch(['B', '127.0.0.1', '10002', '127.0.0.1', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        c = launch(['C', '127.0.0.1', '10003', '127.0.0.1', '10002'])
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
        return True
    except P2PTreeTestError:
        finalize(a, b, c)
        return False

def p2p_tree_test_4() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '10001'])
        nap()
        b = launch(['B', '127.0.0.1', '10002', '127.0.0.1', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        c = launch(['C', '127.0.0.1', '10003', '127.0.0.1', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(c, 'connected')
        d = launch(['D', '127.0.0.1', '10004', '127.0.0.1', '10001'])
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
        return True
    except P2PTreeTestError:
        finalize(a, b, c, d)
        return False

def p2p_tree_test_5() -> bool:
    try:
        a = launch(['A', '127.0.0.1', '10001'])
        nap()
        b = launch(['B', '127.0.0.1', '10002', '127.0.0.1', '10001'])
        nap()
        verify_err_line(a, 'accepted')
        verify_err_line(b, 'connected')
        c = launch(['C', '127.0.0.1', '10003', '127.0.0.1', '10002'])
        nap()
        verify_err_line(b, 'accepted')
        verify_err_line(c, 'connected')
        d = launch(['D', '127.0.0.1', '10004', '127.0.0.1', '10003'])
        nap()
        verify_err_line(c, 'accepted')
        verify_err_line(d, 'connected')
        e = launch(['E', '127.0.0.1', '10005', '127.0.0.1', '10004'])
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
        return True
    except P2PTreeTestError:
        finalize(a, b, c, d, e)
        return False

if __name__ == '__main__':
    global_dict = globals().copy()
    for k, v in global_dict.items():
        if k.startswith('p2p_tree_test'):
            print(f'running test {k} ', end = '', flush = True)
            if v():
                print(f' test {k} passed')
            else:
                sys.exit(f' test {k} failed')
