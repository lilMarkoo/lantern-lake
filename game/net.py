"""Online co-op: one player hosts their lake and friends join by address.

Plain TCP carrying one JSON object per line, standard library only (never pickle). Network threads only move
bytes: readers parse lines into a queue, writers drain an outbox, and the game handles every message on its own
thread through Net.poll(). The host is the hub. It hands each guest an id, relays what guests send to everyone
else, and owns the clock and the weather.

On the local network the host also broadcasts a small UDP beacon so the join screen can list nearby lakes.

Over the internet the lake goes through the online server (server/relay.py) when there is one: the host connects
out to it and gets a short room code like K7Q2-M9XT, and friends who type it are passed through to the host. No
router settings, and it works behind any network. The server only passes bytes along; the host still checks every
newcomer exactly as it does a direct one.

Without the server (or when it can't be reached) the router opens the port instead (portmap.py) and friends join
with a longer room code that carries a random key. Anyone connecting from the internet must know that key; the
host also caps connection attempts, bans addresses that keep guessing, and drops connections that flood it.
"""
import hmac
import json
import os
import queue
import socket
import threading
import time

import portmap

PORT = 24680             # TCP, the game itself
BEACON_PORT = 24681      # UDP, "there is a lake here" on the local network
VERSION = 2              # 2: room codes and keys (1.6.0)
MAX_PLAYERS = 4          # the host plus three friends (the dock has three free spots)
MAX_LINE = 32 * 1024     # anything longer is not ours: drop the connection
NAME_MAX = 14
CHAT_MAX = 80
TIMEOUT = 20.0           # seconds of silence before a connection counts as lost
HELLO_WAIT = 8.0
RELAY = ('st', 'chat', 'catch', 'gift', 'race', 'exp')
# guarding a lake that is open to the internet
MAX_PENDING = 8          # connections that haven't said hello yet
MAX_PENDING_PER_IP = 3
MAX_CONNS = 16
BAD_KEYS_BEFORE_BAN = 5
BAN_SECONDS = 600
MSG_BURST = 300          # messages a connection may send at once...
MSG_RATE = 40.0          # ...and per second after that (the game sends about 10)
# the online server (server/relay.py), in Europe. LANTERN_RELAY=host:port overrides it, '-' turns it off
RELAY_ADDR = '92.5.166.93'
RELAY_PORT = 24690
RELAY_VERSION = 1
RELAY_CODE_LEN = 8
RELAY_PING = 20.0


def relay_addr():
    """(host, port) of the online server, or None when there isn't one."""
    text = os.environ.get('LANTERN_RELAY', RELAY_ADDR).strip()
    if not text or text == '-':
        return None
    host, port = text, RELAY_PORT
    if text.count(':') == 1:
        host, p = text.rsplit(':', 1)
        try:
            port = int(p)
        except ValueError:
            return None
    return (host, port) if host and 0 < port < 65536 else None


def parse_relay_code(text):
    """'k7q2-m9xt' -> 'K7Q2M9XT', or None when it isn't one of the online server's codes."""
    s = ''.join(ch for ch in str(text).upper() if ch not in ' -_')
    s = ''.join(portmap.LOOKALIKE.get(ch, ch) for ch in s)
    if len(s) != RELAY_CODE_LEN or any(ch not in portmap.ALPHABET for ch in s):
        return None
    if '.' in text or ':' in text:
        return None
    return s


def show_relay_code(code):
    return code[:4] + '-' + code[4:]


class RelayHost:
    """Host: keeps a room open on the online server, and opens a line through it for each friend who joins.
    state: 'working' (connecting), 'open' (code is ready), 'failed' (couldn't reach the server; why says why)."""

    def __init__(self, net, addr, stop, on_fail):
        self.net = net
        self.addr = addr
        self.stop = stop
        self.on_fail = on_fail
        self.state = 'working'
        self.code = None
        self.tok = None
        self.why = ''
        self.sock = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        wait = 2.0
        while not self.stop.is_set():
            try:
                sock = socket.create_connection(self.addr, timeout=6)
            except OSError:
                if self.code is None:
                    self.why = "Couldn't reach the online server."
                    self.on_fail()                     # the router gets a go first, so nothing reads 'failed'
                    self.state = 'failed'
                    return
                self.state = 'working'                 # it was open: keep trying, the room is kept a while
                if self.stop.wait(wait):
                    return
                wait = min(30.0, wait * 1.6)
                continue
            self.sock = sock
            hello = {'t': 'r_host', 'v': RELAY_VERSION}
            if self.code:
                hello.update(code=self.code, tok=self.tok)
            denied = self._session(sock, hello)
            self.sock = None
            try:
                sock.close()
            except OSError:
                pass
            if denied is not None:
                self.why = denied
                if self.code is None:
                    self.on_fail()
                self.state = 'failed'
                return
            if self.stop.is_set():
                return
            self.state = 'working'
            wait = 2.0
            if self.stop.wait(wait):
                return

    def _session(self, sock, hello):
        """One connection to the server. Returns a refusal message, or None when the connection just ended."""
        sock.settimeout(1.0)
        try:
            sock.sendall(_line(hello))
        except OSError:
            return None
        buf = b''
        last_ping = time.time()
        heard = time.time()
        while not self.stop.is_set():
            if time.time() - last_ping > RELAY_PING:
                last_ping = time.time()
                try:
                    sock.sendall(_line({'t': 'r_ping'}))
                except OSError:
                    return None
            try:
                data = sock.recv(4096)
            except socket.timeout:
                if time.time() - heard > RELAY_PING * 3.5:
                    return None
                continue
            except OSError:
                return None
            if not data:
                return None
            heard = time.time()
            buf += data
            if len(buf) > MAX_LINE:
                return None
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                try:
                    m = json.loads(line.decode('utf-8'))
                except Exception:
                    continue
                if not isinstance(m, dict):
                    continue
                t = m.get('t')
                if t == 'r_room' and isinstance(m.get('code'), str) and isinstance(m.get('tok'), str):
                    self.code, self.tok = m['code'], m['tok']
                    self.state = 'open'
                elif t == 'r_guest' and isinstance(m.get('sid'), int):
                    threading.Thread(target=self._line_for, args=(m['sid'],), daemon=True).start()
                elif t == 'deny':
                    return str(m.get('why', 'The online server said no.'))[:120]
        return None

    def _line_for(self, sid):
        """Open a line through the server for friend sid; from then on it's like they connected directly."""
        try:
            sock = socket.create_connection(self.addr, timeout=6)
            sock.sendall(_line({'t': 'r_accept', 'sid': sid, 'tok': self.tok}))
        except OSError:
            return
        if self.stop.is_set():
            sock.close()
            return
        self.net._adopt(sock, 'relay', relayed=True)

    def close(self):
        s = self.sock
        if s is not None:
            try:
                s.sendall(_line({'t': 'r_close'}))
            except OSError:
                pass
            try:
                s.close()
            except OSError:
                pass


def _line(msg):
    return (json.dumps(msg, separators=(',', ':')) + '\n').encode('utf-8')


def needs_key(ip):
    """Only connections from the open internet must know the room key; home networks and VPNs join freely."""
    return portmap.is_public(ip)


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

    def __init__(self, sock, inbox, cid, ip=''):
        self.sock = sock
        self.inbox = inbox
        self.cid = cid
        self.ip = ip
        self.alive = True
        self.last = time.time()
        self.tokens = float(MSG_BURST)
        self.tok_t = time.time()
        self.guard = False          # the host guards the guests it accepted; guests trust the host they chose
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
            # flood guard: a token bucket, refilled over time; nothing the real game sends comes near it
            if self.guard:
                now = time.time()
                self.tokens = min(float(MSG_BURST), self.tokens + (now - self.tok_t) * MSG_RATE)
                self.tok_t = now
                self.tokens -= data.count(b'\n')
                if self.tokens < 0:
                    break
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
        self.key = b''           # host: the room key; guest: the key from the code they typed
        self.opener = None       # host: portmap.Opener while the lake is open to the internet
        self.relay = None        # host: RelayHost while the lake is open through the online server
        self.bad = {}            # host: ip -> [wrong keys, first try time]
        self.banned = {}         # host: ip -> banned until

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
        self.key = portmap.new_key()
        self.bad, self.banned = {}, {}
        threading.Thread(target=self._accept, args=(srv, self.stop, self.inbox), daemon=True).start()
        if not bind:
            threading.Thread(target=self._beacon, args=(self.stop,), daemon=True).start()
        return None

    # ---------------------------------------------------------------- the internet
    def open_online(self, ssdp_target=portmap.SSDP, stun=portmap.stun_address):
        """Host: get a room code, through the online server when there is one, otherwise by asking the router to
        open the port (in the background either way). If the server can't be reached, the router is tried."""
        if self.role != 'host':
            return
        if self.relay is not None:
            self.relay.close()
            self.relay = None
        if self.opener is not None:
            self.opener.close()
            self.opener = None
        addr = relay_addr()
        if addr:
            stop = self.stop
            self.relay = RelayHost(self, addr, stop,
                                   lambda: stop.is_set() or self._open_router(ssdp_target, stun)).start()
        else:
            self._open_router(ssdp_target, stun)

    def _open_router(self, ssdp_target, stun):
        self.opener = portmap.Opener(self.port, ssdp_target, stun).start()

    def online_state(self):
        """None (not trying), or working, open, manual, shared or failed."""
        r = self.relay
        if r is not None and (r.state != 'failed' or self.opener is None):
            return r.state
        return self.opener.state if self.opener is not None else None

    def online_why(self):
        r = self.relay
        if self.opener is not None:
            return self.opener.why
        return r.why if r is not None else ''

    def via_server(self):
        """True while the room code is the online server's."""
        return self.relay is not None and self.relay.state == 'open' and bool(self.relay.code)

    def room_code(self):
        r = self.relay
        if r is not None and r.code and r.state != 'failed':
            return show_relay_code(r.code)
        return self.opener.code(self.key) if self.opener is not None else None

    def _accept(self, srv, stop, inbox):
        while not stop.is_set():
            try:
                sock, addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self._adopt(sock, addr[0], inbox=inbox)

    def _adopt(self, sock, ip, relayed=False, inbox=None):
        """Host: take on a new connection (straight in, or a line through the online server)."""
        now = time.time()
        with self.lock:
            if self.role != 'host':
                refuse = True
            elif self.banned.get(ip, 0) > now:
                refuse = True
            else:
                self.banned.pop(ip, None)
                pending = [c for c in self.conns.values() if c.alive and not c.hello]
                refuse = (len(self.conns) >= MAX_CONNS or len(pending) >= MAX_PENDING
                          or sum(1 for c in pending if c.ip == ip) >= MAX_PENDING_PER_IP)
            if refuse:
                try:
                    sock.close()
                except OSError:
                    pass
                return
            cid = self.next_id
            self.next_id += 1
            conn = Conn(sock, inbox or self.inbox, cid, ip)
            conn.guard = True
            conn.hello = False
            conn.born = now
            conn.relayed = relayed          # the server checked the room code; there's no key to ask for
            self.conns[cid] = conn
        conn.start()

    def _wrong_key(self, ip):
        now = time.time()
        n, t0 = self.bad.get(ip, (0, now))
        if now - t0 > BAN_SECONDS:
            n, t0 = 0, now
        n += 1
        self.bad[ip] = (n, t0)
        if n >= BAD_KEYS_BEFORE_BAN:
            with self.lock:
                self.banned[ip] = now + BAN_SECONDS
            self.bad.pop(ip, None)

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
        """Start connecting in the background, to a room code or an address. Returns an error message or None."""
        key = b''
        rcode = parse_relay_code(addr) if relay_addr() else None
        code = None if rcode else portmap.parse_code(addr)
        if rcode:
            host, port = relay_addr()
        elif code:
            host, port, key = code
        elif portmap.looks_like_code(addr):
            return "That room code doesn't look right. Check it letter by letter (or paste it with Ctrl+V)."
        else:
            try:
                host, port = parse_addr(addr)
            except ValueError:
                return 'That address does not look right. Paste a room code, or try something like 192.168.1.20'
        self.close()
        self.key = key
        self.stop = threading.Event()
        self.inbox = queue.Queue()
        self.role = 'joining'
        self.name = self.clean_name(name)
        self.join_t = time.time()
        self.peers = {}
        threading.Thread(target=self._connect, args=(host, port, self.stop, self.inbox, rcode), daemon=True).start()
        return None

    def _connect(self, host, port, stop, inbox, rcode=None):
        try:
            sock = socket.create_connection((host, port), timeout=6)
        except OSError as e:
            if not stop.is_set():
                why = 'Nobody answered at that address.'
                if rcode:
                    why = "Couldn't reach the online server. Check your internet connection."
                elif isinstance(e, ConnectionRefusedError):
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
        if rcode:
            conn.send({'t': 'r_join', 'code': rcode, 'v': RELAY_VERSION})     # the server passes us through
        conn.send({'t': 'hello', 'v': VERSION, 'name': self.name, 'key': self.key.hex()})

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
            if not getattr(conn, 'relayed', False) and needs_key(conn.ip):
                given = msg.get('key')
                try:
                    given = bytes.fromhex(given) if isinstance(given, str) and len(given) <= 64 else b''
                except ValueError:
                    given = b''
                if not self.key or not hmac.compare_digest(given, self.key):
                    self._wrong_key(conn.ip)
                    conn.send({'t': 'deny', 'why': "That room code isn't right, or the lake was reopened with a "
                                                   'new one. Ask your friend for the code again.'})
                    conn.finish()
                    return
            if msg.get('v') != VERSION:
                conn.send({'t': 'deny', 'why': "Your game is a different version from the host's. Update it from "
                                               'the launcher.'})
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
        if self.relay is not None:
            rl, self.relay = self.relay, None
            threading.Thread(target=rl.close, daemon=True).start()
        if self.opener is not None:
            op, self.opener = self.opener, None
            # not a daemon thread: closing the port on the router still finishes if the game is quitting
            threading.Thread(target=op.close).start()
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
