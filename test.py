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
    if s not in p.stdout.readline():
        raise P2PTreeTestError()

def verify_err_line(p: subprocess.Popen, s: str) -> None:
    if s not in p.stderr.readline():
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
        if a.poll() is None:
            a.kill()
            raise P2PTreeTestError()
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
        if b.poll() is None:
            b.kill()
            raise P2PTreeTestError()
        write_line(a, '')
        nap()
        if a.poll() is None:
            a.kill()
            raise P2PTreeTestError()
        write_line(c, '')
        nap()
        if c.poll() is None:
            c.kill()
            raise P2PTreeTestError()
        return True
    except P2PTreeTestError:
        finalize(a, b, c)
        return False

if __name__ == '__main__':
    global_dict = globals().copy()
    for k, v in global_dict.items():
        if k.startswith('p2p_tree_test'):
            print(f'running test {k}...')
            if v():
                print(f'test {k} passed')
            else:
                sys.exit(f'test {k} failed')
