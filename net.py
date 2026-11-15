"""Online co-op: one player hosts their lake and friends join by address.

Plain TCP carrying one JSON object per line, standard library only (never pickle). Network threads only move
bytes: readers parse lines into a queue, writers drain an outbox, and the game handles every message on its own
thread through Net.poll(). The host is the hub. It hands each guest an id, relays what guests send to everyone
else, and owns the clock and the weather.

On the local network the host also broadcasts a small UDP beacon so the join screen can list nearby lakes.
"""
import json
import queue
import socket
import threading
import time

PORT = 24680             # TCP, the game itself
BEACON_PORT = 24681      # UDP, "there is a lake here" on the local network
VERSION = 1
MAX_PLAYERS = 4          # the host plus three friends (the dock has three free spots)
MAX_LINE = 32 * 1024     # anything longer is not ours: drop the connection
NAME_MAX = 14
CHAT_MAX = 80
TIMEOUT = 20.0           # seconds of silence before a connection counts as lost
HELLO_WAIT = 8.0
RELAY = ('st', 'chat', 'catch', 'gift', 'race')


def clean_text(s, n, allowed):
    """Keep only characters the pixel font can draw, collapse spaces and cap the length."""
    s = ''.join(ch for ch in str(s) if ch in allowed or ch == ' ')
    return ' '.join(s.split())[:n]


def lan_address():
    """This computer's address on the local network. Connecting a UDP socket sends no packets."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'
    finally:
        s.close()


def parse_addr(text):
    """'192.168.1.20' or 'name.example:24680' -> (host, port). Raises ValueError."""
    text = text.strip()
    host, port = text, PORT
    if text.count(':') == 1:
        host, p = text.rsplit(':', 1)
        port = int(p)
    if not host or ' ' in host or not 0 < port < 65536:
        raise ValueError(text)
    return host, port


class Conn:
    """One TCP connection: a reader thread that queues parsed messages and a writer thread with an outbox,
    so the game never waits on the network."""

    def __init__(self, sock, inbox, cid):
        self.sock = sock
        self.inbox = inbox
        self.cid = cid
        self.alive = True
        self.last = time.time()
        self.outbox = queue.Queue(maxsize=600)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        sock.settimeout(1.0)

    def start(self):
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._write, daemon=True).start()

    def _read(self):
        buf = b''
        while self.alive:
            try:
                data = self.sock.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            self.last = time.time()
            buf += data
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode('utf-8'))
                except Exception:          # bad JSON, bad UTF-8, absurd nesting: skip the line
                    continue
                if isinstance(msg, dict) and isinstance(msg.get('t'), str) and not msg['t'].startswith('_'):
                    self.inbox.put((self.cid, msg))
            if len(buf) > MAX_LINE:
                break
        self.close()
        self.inbox.put((self.cid, {'t': '_closed'}))

    def _write(self):
        while True:
            data = self.outbox.get()
            if data is None or not self.alive:
                break
            if data == b'FIN':
                # finish(): everything queued is sent, now say goodbye but let the other side read it
                try:
                    self.sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                return
            try:
                self.sock.sendall(data)
            except OSError:
                break
        self.close()

    def finish(self):
        """Close after the queued messages are delivered (used to send a refusal)."""
        try:
            self.outbox.put_nowait(b'FIN')
        except queue.Full:
            self.close()

    def send(self, msg):
        if not self.alive:
            return False
        try:
            self.outbox.put_nowait((json.dumps(msg, separators=(',', ':')) + '\n').encode('utf-8'))
            return True
        except queue.Full:                 # the other side stopped reading: let it go
            self.close()
            return False

    def close(self):
        if not self.alive:
            return
        self.alive = False
        try:
            self.outbox.put_nowait(None)
        except queue.Full:
            pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class Net:
    """The game's side of co-op. role is None (playing alone), 'joining', 'guest' or 'host'."""

    def __init__(self, allowed_chars=None):
        self.allowed = allowed_chars or set(chr(c) for c in range(33, 127))
        self.role = None
        self.inbox = queue.Queue()
        self.conns = {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.me = 0
        self.name = 'Angler'
        self.host_name = ''
        self.port = PORT
        self.peers = {}          # id -> dict(name, st, joined); everyone except me
        self.world = None        # host: the latest world message, sent to newcomers
        self.server = None
        self.join_t = 0.0
        self.next_id = 1
        self.found = {}          # LAN lakes heard: (ip, port) -> (name, players, time)
        self._listen = None
        self.sent = self.received = 0

    # ---------------------------------------------------------------- state
    @property
    def online(self):
        return self.role in ('host', 'guest')

    def clean_name(self, s):
        return clean_text(s, NAME_MAX, self.allowed) or 'Angler'

    def clean_chat(self, s):
        return clean_text(s, CHAT_MAX, self.allowed)

    # ---------------------------------------------------------------- hosting
    def host(self, name, port=PORT, bind=''):
        """Open this lake to friends. Returns an error message, or None when it worked.
        bind='127.0.0.1' keeps it on this computer (tests)."""
        self.close()
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((bind, port))
            srv.listen(8)
            srv.settimeout(0.5)
        except OSError as e:
            srv.close()
            return 'Could not open port %d. Is another game already hosting? (%s)' % (port, e.strerror or e)
        self.stop = threading.Event()
        self.inbox = queue.Queue()
        self.server = srv
        self.port = port
        self.role = 'host'
        self.me = 0
        self.name = self.clean_name(name)
        self.peers = {}
        self.next_id = 1
        threading.Thread(target=self._accept, args=(srv, self.stop, self.inbox), daemon=True).start()
        if not bind:
            threading.Thread(target=self._beacon, args=(self.stop,), daemon=True).start()
        return None

    def _accept(self, srv, stop, inbox):
        while not stop.is_set():
            try:
                sock, addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self.lock:
                cid = self.next_id
                self.next_id += 1
                conn = Conn(sock, inbox, cid)
                conn.hello = False
                conn.born = time.time()
                self.conns[cid] = conn
            conn.start()

    def _beacon(self, stop):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            pass
        while not stop.wait(1.5):
            msg = json.dumps({'lantern': VERSION, 'name': self.name, 'port': self.port,
                              'n': 1 + len(self.peers)}).encode('utf-8')
            try:
                s.sendto(msg, ('255.255.255.255', BEACON_PORT))
            except OSError:
                pass
        s.close()

    # ---------------------------------------------------------------- joining
    def join(self, addr, name):
        """Start connecting in the background. Returns an error message or None."""
        try:
            host, port = parse_addr(addr)
        except ValueError:
            return 'That address does not look right. Try something like 192.168.1.20'
        self.close()
        self.stop = threading.Event()
        self.inbox = queue.Queue()
        self.role = 'joining'
        self.name = self.clean_name(name)
        self.join_t = time.time()
        self.peers = {}
        threading.Thread(target=self._connect, args=(host, port, self.stop, self.inbox), daemon=True).start()
        return None

    def _connect(self, host, port, stop, inbox):
        try:
            sock = socket.create_connection((host, port), timeout=6)
        except OSError as e:
            if not stop.is_set():
                why = 'Nobody answered at that address.'
                if isinstance(e, ConnectionRefusedError):
                    why = 'That computer is not hosting a lake right now.'
                elif isinstance(e, socket.gaierror):
                    why = 'Could not find that address.'
                inbox.put((0, {'t': '_failed', 'why': why}))
            return
        if stop.is_set():
            sock.close()
            return
        conn = Conn(sock, inbox, 0)
        with self.lock:
            self.conns = {0: conn}
        conn.start()
        conn.send({'t': 'hello', 'v': VERSION, 'name': self.name})

    # ---------------------------------------------------------------- LAN discovery (join screen)
    def listen_lan(self, on):
        if on and self._listen is None:
            ev = threading.Event()
            self._listen = ev
            threading.Thread(target=self._hear, args=(ev,), daemon=True).start()
        elif not on and self._listen is not None:
            self._listen.set()
            self._listen = None

    def _hear(self, ev):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', BEACON_PORT))
            s.settimeout(0.5)
        except OSError:
            s.close()
            return
        while not ev.is_set():
            try:
                data, (ip, _) = s.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                m = json.loads(data.decode('utf-8'))
                if m.get('lantern') == VERSION:
                    port = int(m.get('port', PORT))
                    self.found[(ip, port)] = (self.clean_name(m.get('name', '')), int(m.get('n', 1)), time.time())
            except Exception:
                continue
        s.close()

    def lan_lakes(self):
        now = time.time()
        return sorted(((ip, port, nm, n) for (ip, port), (nm, n, t) in list(self.found.items()) if now - t < 5),
                      key=lambda e: e[2].lower())

    # ---------------------------------------------------------------- sending
    def send(self, msg):
        """Host: to every guest. Guest: to the host, who passes it on."""
        if self.role == 'host':
            msg['id'] = 0
            for c in self._live():
                if c.hello:
                    c.send(msg)
                    self.sent += 1
        elif self.role == 'guest':
            c = self.conns.get(0)
            if c:
                c.send(msg)
                self.sent += 1

    def _live(self):
        with self.lock:
            return [c for c in self.conns.values() if c.alive]

    def _relay(self, msg, skip):
        for c in self._live():
            if c.hello and c.cid != skip:
                c.send(msg)

    # ---------------------------------------------------------------- receiving (main thread)
    def poll(self):
        """Handle everything that arrived. Returns game events:
        ('joined', id, name) ('left', id, name) ('welcome', msg) ('failed', why) ('lost', why)
        ('chat', id, msg) ('catch', id, msg) ('st', id, msg) ('world', msg) ('sleep', None)"""
        ev = []
        if self.role is None:
            return ev
        now = time.time()
        while True:
            try:
                cid, msg = self.inbox.get_nowait()
            except queue.Empty:
                break
            self.received += 1
            if self.role == 'host':
                self._host_msg(cid, msg, ev)
            else:
                self._guest_msg(msg, ev)
            if self.role is None:
                break
        # quiet connections are gone; guests that never said hello are dropped
        for c in self._live():
            if now - c.last > TIMEOUT or (self.role == 'host' and not c.hello and now - c.born > HELLO_WAIT):
                c.close()
        if self.role == 'joining' and now - self.join_t > HELLO_WAIT + 6:
            self.close()
            ev.append(('failed', 'The lake did not answer. Check the address and try again.'))
        return ev

    def _host_msg(self, cid, msg, ev):
        t = msg['t']
        with self.lock:
            conn = self.conns.get(cid)
        if t == '_closed':
            with self.lock:
                self.conns.pop(cid, None)
            p = self.peers.pop(cid, None)
            if p:
                self._relay({'t': 'leave', 'id': cid}, cid)
                ev.append(('left', cid, p['name']))
            return
        if conn is None or not conn.alive:
            return
        if t == 'hello':
            if conn.hello:
                return
            if msg.get('v') != VERSION:
                conn.send({'t': 'deny', 'why': 'Your game is a different version from the host\'s.'})
                conn.finish()
                return
            if len(self.peers) + 1 >= MAX_PLAYERS:
                conn.send({'t': 'deny', 'why': 'That lake is full (%d anglers).' % MAX_PLAYERS})
                conn.finish()
                return
            name = self.clean_name(msg.get('name', ''))
            taken = {p['name'] for p in self.peers.values()} | {self.name}
            base, k = name, 2
            while name in taken:
                name = '%s %d' % (base[:NAME_MAX - 2], k)
                k += 1
            conn.hello = True
            players = {str(i): {'name': p['name']} for i, p in self.peers.items()}
            players['0'] = {'name': self.name}
            conn.send({'t': 'welcome', 'you': cid, 'name': name, 'players': players, 'world': self.world})
            self.peers[cid] = dict(name=name, st={}, joined=time.time())
            self._relay({'t': 'join', 'id': cid, 'name': name}, cid)
            ev.append(('joined', cid, name))
            return
        if not conn.hello:
            return
        if t in RELAY:
            msg['id'] = cid
            if t == 'chat':
                msg['text'] = self.clean_chat(msg.get('text', ''))
                if not msg['text']:
                    return
            if t == 'st':
                self.peers[cid]['st'] = msg
            self._relay(msg, cid)
            ev.append((t, cid, msg))

    def _guest_msg(self, msg, ev):
        t = msg['t']
        if t == '_failed':
            self.close()
            ev.append(('failed', msg.get('why', 'Could not connect.')))
            return
        if t == '_closed':
            was = self.role
            self.close()
            if was == 'joining':
                ev.append(('failed', 'The host closed the connection.'))
            else:
                ev.append(('lost', '%s closed their lake. You row home to your own.' % (self.host_name or 'The host')))
            return
        if t == 'deny':
            self.close()
            ev.append(('failed', str(msg.get('why', 'The host said no.'))[:90]))
            return
        if t == 'welcome' and self.role == 'joining':
            try:
                self.me = int(msg['you'])
                players = {int(k): v for k, v in dict(msg.get('players') or {}).items()}
            except (KeyError, TypeError, ValueError):
                return
            self.role = 'guest'
            self.name = self.clean_name(msg.get('name', self.name))
            self.peers = {i: dict(name=self.clean_name(v.get('name', '')) if isinstance(v, dict) else 'Angler',
                                  st={}, joined=time.time())
                          for i, v in players.items() if i != self.me}
            self.host_name = self.peers.get(0, {}).get('name', '')
            ev.append(('welcome', msg))
            return
        if self.role != 'guest':
            return
        pid = msg.get('id')
        if not isinstance(pid, int) or pid == self.me:
            pid = None
        if t == 'join' and pid is not None:
            name = self.clean_name(msg.get('name', ''))
            self.peers[pid] = dict(name=name, st={}, joined=time.time())
            ev.append(('joined', pid, name))
        elif t == 'leave' and pid is not None:
            p = self.peers.pop(pid, None)
            if p:
                ev.append(('left', pid, p['name']))
        elif t in RELAY and pid in self.peers:
            if t == 'st':
                self.peers[pid]['st'] = msg
            if t == 'chat':
                msg['text'] = self.clean_chat(msg.get('text', ''))
            ev.append((t, pid, msg))
        elif t == 'world':
            ev.append(('world', msg))
        elif t == 'sleep':
            ev.append(('sleep', None))

    # ---------------------------------------------------------------- shutdown
    def close(self):
        """Leave or stop hosting. Safe to call at any time."""
        self.stop.set()
        if self.server is not None:
            try:
                self.server.close()
            except OSError:
                pass
            self.server = None
        with self.lock:
            conns, self.conns = list(self.conns.values()), {}
        for c in conns:
            c.close()
        self.inbox = queue.Queue()
        self.role = None
        self.peers = {}
        self.world = None
        self.host_name = ''
