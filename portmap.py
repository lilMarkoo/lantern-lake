"""Playing over the internet without a server: room codes, opening a port on the router, and the public address.

A room code packs the host's public IPv4 address, the port and a random key into 19 letters and digits,
like 7KQ2M-9X4TB-HC1PE-W3RA. Friends type or paste it to join. The key keeps strangers out even when the port is
open: the host turns away anyone from the internet who doesn't know it.

The port is opened with UPnP, the "let a game open a port" feature most home routers have. Nothing is sent
anywhere except to the router, plus one small STUN request (a public "what is my address" service, the same
kind video calls use) to learn the public address and spot a shared connection. Nothing about the player is
sent. Standard library only. Everything blocking runs on a background thread.
"""
import hashlib
import ipaddress
import os
import re
import socket
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

# Crockford base32: no I, L, O or U, so a code read aloud or copied by hand still works
ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
LOOKALIKE = {'O': '0', 'I': '1', 'L': '1'}
KEY_BYTES = 5
CODE_LEN = 19            # 18 data symbols (11 bytes) and one check symbol

SSDP = ('239.255.255.250', 1900)
SEARCH = ('urn:schemas-upnp-org:device:InternetGatewayDevice:1',
          'urn:schemas-upnp-org:device:InternetGatewayDevice:2',
          'urn:schemas-upnp-org:service:WANIPConnection:1')
SERVICES = ('urn:schemas-upnp-org:service:WANIPConnection:2',
            'urn:schemas-upnp-org:service:WANIPConnection:1',
            'urn:schemas-upnp-org:service:WANPPPConnection:1')
STUN_SERVERS = (('stun.cloudflare.com', 3478), ('stun.l.google.com', 19302))
LEASE = 3600             # seconds; renewed while hosting, so a crash never leaves the port open for long
DESCRIPTION = 'Lantern Lake'
MAX_XML = 512 * 1024


# ---------------------------------------------------------------------------- room codes
def new_key():
    return os.urandom(KEY_BYTES)


def _check(data):
    return ALPHABET[hashlib.sha256(data).digest()[0] & 31]


def make_code(ip, port, key):
    data = socket.inet_aton(ip) + struct.pack('>H', port) + key
    n = int.from_bytes(data, 'big')
    syms = []
    for _ in range(18):
        syms.append(ALPHABET[n & 31])
        n >>= 5
    s = ''.join(reversed(syms)) + _check(data)
    return '-'.join(s[i:i + 5] for i in range(0, len(s), 5))


def parse_code(text):
    """'7kq2m 9x4tb-hc1pe-w3ra' -> (ip, port, key), or None when it isn't a room code (or has a typo)."""
    s = ''.join(ch for ch in str(text).upper() if ch not in ' -_')
    s = ''.join(LOOKALIKE.get(ch, ch) for ch in s)
    if len(s) != CODE_LEN or any(ch not in ALPHABET for ch in s):
        return None
    n = 0
    for ch in s[:18]:
        n = (n << 5) | ALPHABET.index(ch)
    if n >> 88:
        return None
    data = n.to_bytes(11, 'big')
    if _check(data) != s[18]:
        return None
    ip = socket.inet_ntoa(data[:4])
    port = struct.unpack('>H', data[4:6])[0]
    if not port:
        return None
    return ip, port, data[6:]


def looks_like_code(text):
    """True when the text is meant as a room code (even a mistyped one) rather than an address."""
    s = ''.join(ch for ch in str(text) if ch not in ' -_')
    return len(s) >= 15 and '.' not in s and ':' not in s and s.isalnum()


def is_public(ip):
    """True for an address on the open internet (not home, loopback, link-local or a provider's shared range)."""
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


# ---------------------------------------------------------------------------- UPnP
class UPnPError(Exception):
    def __init__(self, code, text=''):
        Exception.__init__(self, '%s %s' % (code, text))
        self.code = code


def local_ip_toward(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((host, 1900))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def lan_ip():
    """This computer's address on the home network (connecting a UDP socket sends nothing)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def discover(timeout=2.5, target=SSDP):
    """Routers on this network that answer a UPnP search, as [(responder ip, description url)]."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    found = []
    try:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        s.settimeout(0.3)
        targets = [target]
        lan = lan_ip() if target == SSDP else None
        if lan and not lan.startswith('127.'):
            # PCs with VPN or virtual adapters otherwise send the search out of the wrong one
            try:
                s.bind((lan, 0))
                s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(lan))
            except OSError:
                pass
            base = lan.rsplit('.', 1)[0]
            targets += [(base + '.1', 1900), (base + '.254', 1900)]     # where home routers usually live
        for st in SEARCH:
            msg = ('M-SEARCH * HTTP/1.1\r\nHOST: %s:%d\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: %s\r\n\r\n'
                   % (SSDP[0], SSDP[1], st)).encode('ascii')
            for dst in targets:
                try:
                    s.sendto(msg, dst)
                except OSError:
                    pass
        end = time.time() + timeout
        while time.time() < end:
            try:
                data, (ip, _) = s.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            m = re.search(rb'(?im)^location:\s*(\S+)', data)
            if not m:
                continue
            loc = m.group(1).decode('ascii', 'replace')
            u = urllib.parse.urlparse(loc)
            # only a device on this network may answer, and only about itself
            if u.scheme != 'http' or u.hostname != ip or is_public(ip):
                continue
            if (ip, loc) not in found:
                found.append((ip, loc))
                end = min(end, time.time() + 0.6)     # the first answer is usually the router; wait a moment more
    finally:
        s.close()
    return found


def _get(url, timeout=4):
    req = urllib.request.Request(url, headers={'User-Agent': 'LanternLake/1 UPnP/1.1'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(MAX_XML + 1)
    if len(data) > MAX_XML:
        raise UPnPError('size', 'description too big')
    return data.decode('utf-8', 'replace')


def _tag(xml, name):
    m = re.search(r'<(?:\w+:)?%s\s*>\s*([^<]*?)\s*</(?:\w+:)?%s\s*>' % (name, name), xml)
    return m.group(1) if m else None


def find_service(location):
    """(control url, service type) of the router's port-mapping service, from its description."""
    xml = _get(location)
    base = _tag(xml, 'URLBase') or location
    for block in re.findall(r'<(?:\w+:)?service\s*>(.*?)</(?:\w+:)?service\s*>', xml, re.S):
        st = _tag(block, 'serviceType')
        ctl = _tag(block, 'controlURL')
        if st in SERVICES and ctl:
            url = urllib.parse.urljoin(base, ctl)
            # the control address must stay on the router that answered
            if urllib.parse.urlparse(url).hostname != urllib.parse.urlparse(location).hostname:
                continue
            return url, st
    raise UPnPError('noservice', 'the router has no port mapping service')


def soap(control, service, action, args=(), timeout=4):
    body = ''.join('<%s>%s</%s>' % (k, escape(str(v)), k) for k, v in args)
    env = ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
           's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
           '<u:%s xmlns:u="%s">%s</u:%s></s:Body></s:Envelope>' % (action, service, body, action))
    req = urllib.request.Request(control, data=env.encode('utf-8'), method='POST', headers={
        'Content-Type': 'text/xml; charset="utf-8"', 'SOAPAction': '"%s#%s"' % (service, action),
        'User-Agent': 'LanternLake/1 UPnP/1.1'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            xml = r.read(MAX_XML).decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        xml = e.read(MAX_XML).decode('utf-8', 'replace')
        raise UPnPError(_tag(xml, 'errorCode') or e.code, _tag(xml, 'errorDescription') or '')
    out = {}
    for k, v in re.findall(r'<(?:\w+:)?(New\w+)\s*>([^<]*)</', xml):
        out[k] = v.strip()
    return out


# ---------------------------------------------------------------------------- STUN (public address)
def stun_address(servers=STUN_SERVERS, timeout=2.0):
    """This connection's public IPv4 address as the internet sees it, or None."""
    for host, port in servers:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(timeout)
            tid = os.urandom(12)
            s.sendto(struct.pack('>HHI', 1, 0, 0x2112A442) + tid, (host, port))
            data, _ = s.recvfrom(2048)
        except OSError:
            continue
        finally:
            s.close()
        if len(data) < 20 or data[8:20] != tid:
            continue
        i = 20
        while i + 4 <= len(data):
            atype, alen = struct.unpack('>HH', data[i:i + 4])
            val = data[i + 4:i + 4 + alen]
            if atype in (0x0020, 0x8020) and len(val) >= 8 and val[1] == 1:
                return socket.inet_ntoa(bytes(b ^ c for b, c in zip(val[4:8], struct.pack('>I', 0x2112A442))))
            if atype == 0x0001 and len(val) >= 8 and val[1] == 1:
                return socket.inet_ntoa(val[4:8])
            i += 4 + alen + (-alen % 4)
    return None


# ---------------------------------------------------------------------------- the door opener
class Opener:
    """Opens the hosting port to the internet on a background thread and keeps it open until close().

    state: 'working', then 'open' (the router opened the port), 'manual' (we know the public address but the
    router didn't open the port: forward it by hand), 'shared' (the internet provider shares one address
    between many homes, so friends can't reach this lake directly) or 'failed' (no public address at all).
    """

    def __init__(self, port, ssdp_target=SSDP, stun=stun_address):
        self.port = port
        self.ssdp_target = ssdp_target
        self.stun = stun
        self.state = 'working'
        self.why = ''
        self.public_ip = None
        self.public_port = port
        self.local_ip = None
        self.mapped = None          # (control, service, external port) while the router holds our mapping
        self.lease = LEASE
        self.stop = threading.Event()
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        try:
            self._open()
        except Exception as e:                     # a router doing something odd must never crash the game
            self.why = 'Something went wrong while opening your lake (%s).' % type(e).__name__
            self.state = 'failed'
            return
        if self.state == 'open' and self.lease:
            while not self.stop.wait(self.lease * 0.45):
                self._renew()

    def _open(self):
        upnp_ip, upnp_why = None, ''
        try:
            upnp_ip = self._upnp()
        except UPnPError as e:
            upnp_why = self._explain(e)
        except (OSError, ValueError) as e:
            upnp_why = "Your router didn't answer the request to open a port (%s)." % type(e).__name__
        if self.stop.is_set():
            self._unmap()
            return
        seen = self.stun() if self.stun else None
        if self.mapped:
            if upnp_ip and not is_public(upnp_ip):
                self.why = ('Your internet provider shares one address between many homes, so friends '
                            "can't reach your lake directly. Use Tailscale, or let a friend host.")
                self.state = 'shared'
                self._unmap()
                return
            if seen and upnp_ip and seen != upnp_ip:
                self.why = ('Your router sits behind another router, so the port only opened halfway. Forward '
                            'TCP port %d on the outer router too, or use Tailscale.' % self.port)
                self.public_ip = seen
                self.state = 'manual'
                return
            self.public_ip = upnp_ip or seen
            self.state = 'open' if self.public_ip else 'failed'
            if not self.public_ip:
                self.why = "Couldn't find your public address."
            return
        if seen and is_public(seen):
            self.public_ip = seen
            self.why = (upnp_why or "Your router didn't open the port.") + \
                ' Friends can still join if you forward TCP port %d to %s on your router.' % (
                    self.port, self.local_ip or 'this computer')
            self.state = 'manual'
        else:
            self.why = (upnp_why or "Your router didn't open the port.") + ' Use Tailscale, or let a friend host.'
            self.state = 'failed'

    @staticmethod
    def _explain(e):
        if e.code == 'noservice':
            return "Your router doesn't offer automatic port opening."
        if str(e.code) in ('606', '401', '403'):
            return 'Your router has automatic port opening (UPnP) switched off.'
        if str(e.code) == '718':
            return 'Another device already uses that port on your router.'
        return "Your router said no to opening a port (%s)." % e.code

    def _upnp(self):
        found = discover(target=self.ssdp_target)
        if not found:
            raise UPnPError('noservice', 'no router answered')
        err = None
        for ip, loc in found:
            try:
                control, service = find_service(loc)
            except (UPnPError, OSError, ValueError) as e:
                err = e
                continue
            self.local_ip = local_ip_toward(ip)
            if not self.local_ip:
                continue
            ext_ip = soap(control, service, 'GetExternalIPAddress').get('NewExternalIPAddress', '')
            for ext in (self.port, self.port + 1, self.port + 2, self.port + 7, self.port + 13):
                if self.stop.is_set():
                    return None
                try:
                    self._add(control, service, ext)
                except UPnPError as e:
                    err = e
                    if str(e.code) == '718':               # taken: maybe by an earlier Lantern Lake of ours
                        if self._ours(control, service, ext):
                            try:
                                soap(control, service, 'DeletePortMapping',
                                     [('NewRemoteHost', ''), ('NewExternalPort', ext), ('NewProtocol', 'TCP')])
                                self._add(control, service, ext)
                            except UPnPError as e2:
                                err = e2
                                continue
                        else:
                            continue
                    else:
                        raise
                with self.lock:
                    self.mapped = (control, service, ext)
                self.public_port = ext
                return ext_ip
        raise err or UPnPError('noservice')

    def _add(self, control, service, ext):
        args = [('NewRemoteHost', ''), ('NewExternalPort', ext), ('NewProtocol', 'TCP'),
                ('NewInternalPort', self.port), ('NewInternalClient', self.local_ip), ('NewEnabled', 1),
                ('NewPortMappingDescription', DESCRIPTION), ('NewLeaseDuration', self.lease)]
        try:
            soap(control, service, 'AddPortMapping', args)
        except UPnPError as e:
            if str(e.code) == '725' and self.lease:         # this router only takes permanent mappings
                self.lease = 0
                args[-1] = ('NewLeaseDuration', 0)
                soap(control, service, 'AddPortMapping', args)
            else:
                raise

    def _ours(self, control, service, ext):
        try:
            e = soap(control, service, 'GetSpecificPortMappingEntry',
                     [('NewRemoteHost', ''), ('NewExternalPort', ext), ('NewProtocol', 'TCP')])
        except (UPnPError, OSError):
            return False
        return e.get('NewInternalClient') == self.local_ip and e.get('NewPortMappingDescription') == DESCRIPTION

    def _renew(self):
        with self.lock:
            m = self.mapped
        if not m:
            return
        try:
            self._add(m[0], m[1], m[2])
        except (UPnPError, OSError):
            pass

    def _unmap(self):
        with self.lock:
            m, self.mapped = self.mapped, None
        if m:
            try:
                soap(m[0], m[1], 'DeletePortMapping',
                     [('NewRemoteHost', ''), ('NewExternalPort', m[2]), ('NewProtocol', 'TCP')], timeout=2)
            except (UPnPError, OSError):
                pass

    def code(self, key):
        if self.state in ('open', 'manual') and self.public_ip:
            return make_code(self.public_ip, self.public_port, key)
        return None

    def close(self):
        """Close the port again. Quick: at most a couple of seconds, even with a slow router."""
        self.stop.set()
        self._unmap()
