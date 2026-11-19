"""Check a Lantern Lake relay from your own computer: opens a room, joins it, and passes a message through.

    python server/check.py 203.0.113.7          (or host:port; the default port is 24690)

Nothing about you is sent: a made-up room is opened and closed again.
"""
import json
import socket
import sys
import time


def line(msg):
    return (json.dumps(msg) + '\n').encode('utf-8')


def read_line(sock, wait=8.0):
    sock.settimeout(wait)
    buf = b''
    while b'\n' not in buf:
        data = sock.recv(4096)
        if not data:
            raise ConnectionError('the server closed the connection')
        buf += data
    return json.loads(buf.split(b'\n', 1)[0].decode('utf-8'))


def main(target):
    host, port = target, 24690
    if target.count(':') == 1:
        host, p = target.rsplit(':', 1)
        port = int(p)
    t0 = time.time()
    try:
        ctrl = socket.create_connection((host, port), timeout=8)
    except OSError as e:
        print("Can't reach %s:%d (%s)." % (host, port, e))
        print('Check the server is running (sudo systemctl status lantern-relay), the ingress rule for TCP %d '
              "in Oracle's security list, and the public IP." % port)
        return 1
    ms = (time.time() - t0) * 1000
    ctrl.sendall(line({'t': 'r_host', 'v': 1}))
    room = read_line(ctrl)
    if room.get('t') != 'r_room':
        print('Unexpected answer:', room)
        return 1
    print('Connected in %.0f ms. Opened a test room: %s-%s' % (ms, room['code'][:4], room['code'][4:]))
    guest = socket.create_connection((host, port), timeout=8)
    guest.sendall(line({'t': 'r_join', 'code': room['code'], 'v': 1}))
    ask = read_line(ctrl)
    if ask.get('t') != 'r_guest':
        print('Unexpected answer:', ask)
        return 1
    data = socket.create_connection((host, port), timeout=8)
    data.sendall(line({'t': 'r_accept', 'sid': ask['sid'], 'tok': room['tok']}))
    guest.sendall(line({'t': 'hello', 'check': 1}))
    got = read_line(data)
    data.sendall(line({'t': 'welcome', 'check': 1}))
    back = read_line(guest)
    ok = got.get('t') == 'hello' and back.get('t') == 'welcome'
    ctrl.sendall(line({'t': 'r_close'}))
    for s in (ctrl, guest, data):
        s.close()
    if ok:
        print('A test friend joined and messages went both ways. The relay works!')
        return 0
    print('Messages did not come through:', got, back)
    return 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
