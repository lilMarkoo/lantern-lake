"""Lantern Lake relay: lets friends join a lake without anyone opening a port on their router.

The host's game connects out to this server and gets a short room code (like K7Q2-M9XT). A friend's game connects
here with that code; the relay asks the host to open a second connection for that friend, then passes bytes
between the two untouched. After the first line on each connection the relay never reads the game's messages:
the host still does everything it does for a direct connection (hello, version check, the lake being full).

Lines before pairing are JSON objects, one per line:
  host -> relay   {"t": "r_host", "v": 1}                     open a room (or "code"+"tok" to take one back)
  relay -> host   {"t": "r_room", "code": "K7Q2M9XT", "tok": "..."}
  relay -> host   {"t": "r_guest", "sid": 12}                 a friend is waiting: connect a data line for them
  host -> relay   {"t": "r_accept", "sid": 12, "tok": "..."}  (on a new connection) this line is for friend 12
  guest -> relay  {"t": "r_join", "code": "K7Q2M9XT", "v": 1}
  relay -> guest  {"t": "deny", "why": "..."}                 the same refusal the game already shows
  either way      {"t": "r_ping"}                             keep-alive on the host's room connection

Guarding it: codes are 8 symbols from a 32-letter alphabet (about a trillion), addresses that keep guessing
are shut out for a while, every address has a cap on connections and rooms, the first line has to arrive
quickly and be short, and each paired connection is limited in speed (the game sends about 10 small messages
a second). Nothing is written to disk. The log only says how many rooms and connections there are; it never
records addresses or room codes.

Standard library only (Python 3.8+). Run:  python3 relay.py --port 24690
"""
import argparse
import asyncio
import hmac
import json
import logging
import os
import signal
import time

VERSION = 1
ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'      # Crockford base32: no I, L, O or U
CODE_LEN = 8
FIRST_LINE_WAIT = 10.0       # seconds to say what you want
FIRST_LINE_MAX = 512         # bytes
HOST_IDLE = 70.0             # a room connection that says nothing this long is gone (the game pings every 20 s)
PIPE_IDLE = 90.0             # a paired connection with no traffic either way this long is gone
ACCEPT_WAIT = 12.0           # the host has this long to open a line for a waiting friend
ROOM_KEEP = 120.0            # a room whose host dropped stays reserved this long, so the host can take it back
MAX_CONNS = 3000
MAX_CONNS_PER_IP = 24
MAX_ROOMS = 1000
MAX_ROOMS_PER_IP = 3
MAX_WAITING_PER_ROOM = 4
MAX_PIPES_PER_ROOM = 6
BAD_CODES_BEFORE_BAN = 8
BAN_SECONDS = 900
RATE = 64 * 1024             # bytes a second, each way, per paired connection...
BURST = 256 * 1024           # ...with this much to spare for a burst (a newcomer gets the whole lake at once)

log = logging.getLogger('relay')


def new_code():
    n = int.from_bytes(os.urandom(5), 'big')
    return ''.join(ALPHABET[(n >> (5 * i)) & 31] for i in range(CODE_LEN))


def clean_code(text):
    s = ''.join(ch for ch in str(text).upper() if ch.isalnum())
    s = s.replace('O', '0').replace('I', '1').replace('L', '1')
    return s if len(s) == CODE_LEN and all(ch in ALPHABET for ch in s) else None


def pack(msg):
    return (json.dumps(msg, separators=(',', ':')) + '\n').encode('utf-8')


class Room:
    def __init__(self, code, ip):
        self.code = code
        self.ip = ip
        self.tok = os.urandom(16).hex()
        self.ctrl = None             # the host's room connection (StreamWriter), None while it's away
        self.gone_at = 0.0
        self.waiting = {}            # sid -> (guest reader, guest writer, future for the host's line)
        self.pipes = 0


class Relay:
    def __init__(self):
        self.rooms = {}
        self.conns = 0
        self.per_ip = {}
        self.bad = {}                # ip -> (wrong codes, first wrong time)
        self.banned = {}             # ip -> until
        self.next_sid = 1
        self.started = time.time()
        self.paired = 0

    # ------------------------------------------------------------------ bookkeeping
    def _banned(self, ip):
        until = self.banned.get(ip)
        if until and until > time.time():
            return True
        self.banned.pop(ip, None)
        return False

    def _wrong_code(self, ip):
        now = time.time()
        n, t0 = self.bad.get(ip, (0, now))
        if now - t0 > BAN_SECONDS:
            n, t0 = 0, now
        n += 1
        self.bad[ip] = (n, t0)
        if n >= BAD_CODES_BEFORE_BAN:
            self.banned[ip] = now + BAN_SECONDS
            self.bad.pop(ip, None)

    def _rooms_of(self, ip):
        return sum(1 for r in self.rooms.values() if r.ip == ip)

    async def sweep(self):
        """Forget rooms whose host never came back, and old guessing records."""
        while True:
            await asyncio.sleep(15)
            now = time.time()
            for code, r in list(self.rooms.items()):
                if r.ctrl is None and now - r.gone_at > ROOM_KEEP:
                    self._drop_room(r)
            for ip, (n, t0) in list(self.bad.items()):
                if now - t0 > BAN_SECONDS:
                    self.bad.pop(ip, None)
            for ip, until in list(self.banned.items()):
                if until < now:
                    self.banned.pop(ip, None)

    def _drop_room(self, r):
        self.rooms.pop(r.code, None)
        for sid, (_, gw, fut) in list(r.waiting.items()):
            if not fut.done():
                fut.cancel()
        r.waiting.clear()

    async def report(self, every):
        while True:
            await asyncio.sleep(every)
            log.info('rooms %d  connections %d  friends joined since start %d', len(self.rooms), self.conns,
                     self.paired)

    # ------------------------------------------------------------------ connections
    async def handle(self, reader, writer):
        peer = writer.get_extra_info('peername') or ('?', 0)
        ip = peer[0]
        if self.conns >= MAX_CONNS or self.per_ip.get(ip, 0) >= MAX_CONNS_PER_IP or self._banned(ip):
            writer.close()
            return
        self.conns += 1
        self.per_ip[ip] = self.per_ip.get(ip, 0) + 1
        handed_off = False
        try:
            line = await asyncio.wait_for(reader.readline(), FIRST_LINE_WAIT)
            if not line or len(line) > FIRST_LINE_MAX or not line.endswith(b'\n'):
                return
            try:
                msg = json.loads(line.decode('utf-8'))
            except Exception:
                return
            if not isinstance(msg, dict):
                return
            t = msg.get('t')
            if t == 'r_host':
                await self._host(reader, writer, ip, msg)
            elif t == 'r_join':
                handed_off = await self._join(reader, writer, ip, msg)
            elif t == 'r_accept':
                handed_off = self._accept(reader, writer, msg, ip)
        except Exception:                # timeouts, resets, over-long lines: just let the connection go
            pass
        finally:
            if not handed_off:
                await self._close(writer)
                self._release(ip)

    def _release(self, ip):
        self.conns -= 1
        n = self.per_ip.get(ip, 1) - 1
        if n <= 0:
            self.per_ip.pop(ip, None)
        else:
            self.per_ip[ip] = n

    @staticmethod
    async def _close(writer):
        try:
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), 3)
        except Exception:
            pass

    @staticmethod
    async def _say(writer, msg):
        writer.write(pack(msg))
        await asyncio.wait_for(writer.drain(), 10)

    # ------------------------------------------------------------------ the host's room
    async def _host(self, reader, writer, ip, msg):
        if msg.get('v') != VERSION:
            await self._say(writer, {'t': 'deny', 'why': 'This game is too old for the online server. Update it.'})
            return
        room = None
        code = clean_code(msg.get('code', ''))
        tok = msg.get('tok')
        if code and isinstance(tok, str):
            r = self.rooms.get(code)
            if r and r.ctrl is None and hmac.compare_digest(r.tok, tok):
                room = r                                 # the host is back after a dropped connection
        if room is None:
            if len(self.rooms) >= MAX_ROOMS or self._rooms_of(ip) >= MAX_ROOMS_PER_IP:
                await self._say(writer, {'t': 'deny', 'why': 'The online server is busy. Try again in a while.'})
                return
            code = new_code()
            while code in self.rooms:
                code = new_code()
            room = Room(code, ip)
            self.rooms[code] = room
        room.ctrl = writer
        await self._say(writer, {'t': 'r_room', 'code': room.code, 'tok': room.tok})
        pinger = asyncio.ensure_future(self._ping(writer))
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), HOST_IDLE)
                if not line:
                    break
                if len(line) > FIRST_LINE_MAX:
                    break
                try:
                    m = json.loads(line.decode('utf-8'))
                except Exception:
                    continue
                if isinstance(m, dict) and m.get('t') == 'r_close':
                    self._drop_room(room)
                    return
        finally:
            pinger.cancel()
            if room.ctrl is writer:
                room.ctrl = None
                room.gone_at = time.time()
                for sid, (_, gw, fut) in list(room.waiting.items()):
                    if not fut.done():
                        fut.cancel()

    async def _ping(self, writer):
        try:
            while True:
                await asyncio.sleep(20)
                await self._say(writer, {'t': 'r_ping'})
        except Exception:
            pass

    # ------------------------------------------------------------------ a friend joining
    async def _join(self, reader, writer, ip, msg):
        code = clean_code(msg.get('code', ''))
        room = self.rooms.get(code) if code else None
        if room is None:
            self._wrong_code(ip)
            await self._say(writer, {'t': 'deny', 'why': "No lake is open with that code. Check it, or ask your "
                                                         'friend for a new one.'})
            return False
        if msg.get('v') != VERSION:
            await self._say(writer, {'t': 'deny', 'why': "Your game is a different version from the host's. "
                                                         'Update it from the launcher.'})
            return False
        if room.ctrl is None:
            await self._say(writer, {'t': 'deny', 'why': "The host's connection dropped. Try again in a minute."})
            return False
        if len(room.waiting) >= MAX_WAITING_PER_ROOM or room.pipes >= MAX_PIPES_PER_ROOM:
            await self._say(writer, {'t': 'deny', 'why': 'That lake is full.'})
            return False
        sid = self.next_sid
        self.next_sid += 1
        fut = asyncio.get_running_loop().create_future()
        room.waiting[sid] = (reader, writer, fut)
        try:
            await self._say(room.ctrl, {'t': 'r_guest', 'sid': sid})
            hr, hw, hip = await asyncio.wait_for(fut, ACCEPT_WAIT)
        except (asyncio.TimeoutError, asyncio.CancelledError, ConnectionError, OSError, AttributeError):
            room.waiting.pop(sid, None)
            try:
                await self._say(writer, {'t': 'deny', 'why': "The host didn't answer. Try again in a moment."})
            except Exception:
                pass
            return False
        room.waiting.pop(sid, None)
        room.pipes += 1
        self.paired += 1
        asyncio.ensure_future(self._pipe(room, ip, hip, reader, writer, hr, hw))
        return True

    def _accept(self, reader, writer, msg, ip):
        """The host opened a line for a waiting friend: pair them (the friend's _join takes it from here)."""
        sid = msg.get('sid')
        tok = msg.get('tok')
        if not isinstance(sid, int) or not isinstance(tok, str):
            return False
        for room in self.rooms.values():
            w = room.waiting.get(sid)
            if w and hmac.compare_digest(room.tok, tok):
                fut = w[2]
                if not fut.done():
                    fut.set_result((reader, writer, ip))
                    return True
        return False

    # ------------------------------------------------------------------ passing bytes along
    async def _pipe(self, room, guest_ip, host_ip, gr, gw, hr, hw):
        last = [time.time()]
        a = asyncio.ensure_future(self._copy(gr, hw, last))
        b = asyncio.ensure_future(self._copy(hr, gw, last))
        try:
            while not (a.done() or b.done()):
                await asyncio.wait([a, b], timeout=10, return_when=asyncio.FIRST_COMPLETED)
                if time.time() - last[0] > PIPE_IDLE:
                    break
        finally:
            a.cancel()
            b.cancel()
            await self._close(gw)
            await self._close(hw)
            room.pipes = max(0, room.pipes - 1)
            self._release(guest_ip)
            self._release(host_ip)

    @staticmethod
    async def _copy(src, dst, last):
        tokens, t0 = float(BURST), time.time()
        try:
            while True:
                data = await src.read(16384)
                if not data:
                    break
                now = time.time()
                last[0] = now
                tokens = min(float(BURST), tokens + (now - t0) * RATE)
                t0 = now
                tokens -= len(data)
                if tokens < 0:
                    await asyncio.sleep(-tokens / RATE)          # over the limit: slow down, don't drop
                dst.write(data)
                await asyncio.wait_for(dst.drain(), 20)
        except Exception:
            pass
        try:
            dst.write_eof()
        except Exception:
            pass


async def main(host, port, report_every):
    relay = Relay()
    server = await asyncio.start_server(relay.handle, host, port, limit=FIRST_LINE_MAX * 2)
    log.info('Lantern Lake relay listening on %s:%d', host or '*', port)
    asyncio.ensure_future(relay.sweep())
    if report_every:
        asyncio.ensure_future(relay.report(report_every))
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (getattr(signal, 'SIGTERM', None), getattr(signal, 'SIGINT', None)):
        if sig is not None:
            try:
                loop.add_signal_handler(sig, stop.set)
            except (NotImplementedError, RuntimeError):
                pass                                    # Windows: Ctrl+C still stops it
    async with server:
        await stop.wait()
    log.info('stopped')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Lantern Lake relay server')
    ap.add_argument('--host', default='', help='address to listen on (default: all)')
    ap.add_argument('--port', type=int, default=24690)
    ap.add_argument('--report', type=float, default=600, help='seconds between status lines in the log (0: never)')
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    try:
        asyncio.run(main(args.host, args.port, args.report))
    except KeyboardInterrupt:
        pass
