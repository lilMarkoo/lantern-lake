# The Lantern Lake online server (relay)

A small server that lets friends join each other's lakes with a short room code like `K7Q2-M9XT`, without anyone
opening a port on their router. The host's game connects out to it, friends' games connect to it with the code,
and it passes the bytes between them. The host's game still does all the checking it always did.

It is one Python file (`relay.py`, standard library only, Python 3.8+). It keeps nothing on disk, and its log only
counts rooms and connections. It never records addresses or codes. One small machine handles hundreds of lakes.

This folder is not part of the game download.

| File | What it is |
| --- | --- |
| `relay.py` | The server |
| `lantern-relay.service` | Runs it on boot as a locked-down service |
| `setup.sh` | Installs or updates it and opens the port: `sudo bash setup.sh` |
| `check.py` | Run on your PC to test a server: `python server/check.py <ip>` |

## Running it on Oracle Cloud (Always Free, Europe)

### 1. Make the account

Sign up for the Free Tier at cloud.oracle.com. It asks for a card to check you're a person, but Always Free
resources aren't charged.

Pick a **home region in Europe**, such as *Germany Central (Frankfurt)* or *Netherlands Northwest (Amsterdam)*.
You can't change the home region later.

### 2. Create the machine

Go to **Compute → Instances → Create instance**.

- **Image:** Canonical Ubuntu 24.04.
- **Shape:** *VM.Standard.E2.1.Micro* (AMD, Always Free) is plenty. *VM.Standard.A1.Flex* (Ampere, 1 OCPU, 6 GB)
  also works.
- **Networking:** create a new virtual cloud network with a **public subnet**, and leave
  **Assign a public IPv4 address** on.
- **SSH keys:** let it generate a key pair, and download the private key.

Create it and wait for it to show **Running**. Note its **Public IP address**.

### 3. Open the port in Oracle's firewall

1. On the instance page, click the subnet, then **Security Lists**, then the default list.
2. Click **Add Ingress Rules** and enter:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `24690`

### 4. Install the relay

From this folder on your PC (PowerShell or Git Bash), replacing the key path and IP with yours:

```bash
scp -i path/to/ssh-key.key relay.py lantern-relay.service setup.sh ubuntu@YOUR.IP.HERE:~
```

```bash
ssh -i path/to/ssh-key.key ubuntu@YOUR.IP.HERE
```

Then, on the server:

```bash
sudo bash setup.sh
```

The script installs the service, opens port 24690 in the machine's own firewall, and says whether the relay is
running.

### 5. Check it from your PC

```bash
python server/check.py YOUR.IP.HERE
```

It should end with *The relay works!*

### 6. Point the game at it

`RELAY_ADDR` in `net.py` is set to this server (92.5.166.93, Frankfurt). Change it there if the server ever moves, then release an update.

To try a relay without a release, start the game with the address in an environment variable:

```bash
LANTERN_RELAY=YOUR.IP.HERE python main.py
```

### Keeping it running

- **Updating:** copy the new `relay.py` up and run `sudo bash setup.sh` again.
- **Logs:**
  ```bash
  journalctl -u lantern-relay -f
  ```
  It writes a status line every 10 minutes.
- **Status:**
  ```bash
  sudo systemctl status lantern-relay
  ```
- **Keep the IP fixed.** If the machine is ever recreated, its IP changes and released games can't find it.
  Either use a *reserved public IP* (Networking → IP management → Reserved public IPs) or put a domain name in
  `RELAY_ADDR` instead of the IP.
- **Idle reclaim:** Oracle may reclaim *idle* Always Free machines, judged on CPU, network and memory use over a
  week. A relay uses very little, so this can happen. Upgrading the account to *Pay As You Go* stops it, and
  Always Free resources stay free. See "Idle Always Free compute instances" in Oracle's Always Free docs.

## Limits built in

- Each address can have at most 24 connections and 3 rooms open.
- Each lake can have up to 4 friends waiting to join and 6 paired connections.
- About 8 wrong codes from one address shuts it out for 15 minutes.
- Each connection has 10 seconds to say what it wants, in a short first line.
- Paired connections are capped at 64 KB/s each way. The game uses a small fraction of that.
- When a host's connection drops, its room is held for 2 minutes. The game reconnects and keeps the same code.
