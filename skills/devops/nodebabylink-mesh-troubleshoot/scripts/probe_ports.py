#!/usr/bin/env python3
"""Banner probe for host:port pairs — the authoritative "is it really open" check.

Why not shell /dev/tcp + head: that pattern returns silent false negatives (observed:
all hosts "closed" while three were open), which leads to a wrong "everything is down"
conclusion. A real connect + recv() also yields the service banner, so one run tells you
both liveness and which machine/service answered.

Usage:
    python3 probe_ports.py 192.168.199.2:22 100.66.1.6:22 100.66.1.6:3457
    python3 probe_ports.py --timeout 6 100.66.1.5:22
    python3 probe_ports.py --http 100.66.1.7:3457 127.0.0.1:3456

Exit code: 0 if every target answered, 1 if any failed.
"""
import argparse
import socket
import sys
import urllib.error
import urllib.request


def probe(host: str, port: int, timeout: float, http: bool) -> tuple[bool, str]:
    if http:
        url = f"http://{host}:{port}/"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                body = r.read(200)
            return True, f"HTTP {r.status} {len(body)}b"
        except urllib.error.HTTPError as e:
            # 404/400 is a healthy answer: the endpoint is alive and refusing the probe.
            return True, f"HTTP {e.code} (alive)"
        except Exception as e:  # noqa: BLE001 - report the class, never crash the sweep
            return False, f"{type(e).__name__}: {e}"
    try:
        with socket.create_connection((host, port), timeout) as s:
            s.settimeout(timeout)
            try:
                banner = s.recv(80).decode(errors="replace").strip()
            except socket.timeout:
                return True, "open (no banner)"
        return True, f"open banner={banner!r}" if banner else "open (empty)"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="host:port ...")
    ap.add_argument("--timeout", type=float, default=4.0)
    ap.add_argument("--http", action="store_true", help="probe with an HTTP GET instead of a raw banner read")
    a = ap.parse_args()

    bad = 0
    for t in a.targets:
        if ":" not in t:
            print(f"{t:32s} SKIP (need host:port)")
            bad += 1
            continue
        host, _, port_s = t.rpartition(":")
        try:
            port = int(port_s)
        except ValueError:
            print(f"{t:32s} SKIP (bad port)")
            bad += 1
            continue
        ok, msg = probe(host, port, a.timeout, a.http)
        print(f"{t:32s} {'OK  ' if ok else 'FAIL'} {msg}")
        if not ok:
            bad += 1
    print(f"\n{len(a.targets) - bad}/{len(a.targets)} reachable")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
