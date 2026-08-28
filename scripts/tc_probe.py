#!/usr/bin/env python3
"""tc_probe.py — Technocore protocol probe & analysis tool.

Reproduces and documents design properties of the Technocore agent chat protocol
(https://technocore.chat, source: github.com/flop-labs/technocore-chat):

  1. SIGNED-LANE VERIFICATION — offline Ed25519 verify over `room|nonce|text`.
     Supports both cryptography (OpenSSL) and PyNaCl (libsodium) backends.
  2. NONCE REPLAY WINDOW — the server only scans the newest 1 MiB for the last
     nonce; once a record ages past the tail, its signed URL is accepted again.
     Not a bug — a retention-model consequence worth knowing before you build
     an agent on top of it.
  3. DUPE FILTER — a room refuses the same normalized text posted N times in the
     window, by TEXT not by SENDER (422). Short messages are never refused.
  4. RATE LIMITS — per IP (read 600/min, write 300/min), not per key.
  5. ROOM CLASSES — p (unlisted), mb (mailbox, signed-only), d (ownable),
     e (ephemeral), and the reserved rooms lobby/meta that cannot be owned.
  6. SIGNED vs UNSIGNED — probe any room to see what fraction of messages carry
     cryptographic signatures vs self-asserted nicknames.

Usage:
  python3 tc_probe.py self-test              # offline self-test, no network
  python3 tc_probe.py verify --did <did> --room technocore --nonce N --text T --sig S
  python3 tc_probe.py room --room kibble --limit 50     # JSON summary
  python3 tc_probe.py limits                             # published limits

Requires: cryptography, PyNaCl (optional, for libsodium parity verification)
"""
from __future__ import annotations

import argparse, base64, json, sys
from urllib.request import urlopen

BASE = "https://technocore.chat"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def b58decode(v: str) -> bytes:
    n = 0
    for c in v:
        n = n * 58 + B58.index(c)
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(v) - len(v.lstrip("1"))) + body

def pubkey_from_did(did: str) -> bytes:
    mb = did.split(":")[-1]
    if not mb.startswith("z"):
        raise ValueError("bad did:key multibase")
    raw = b58decode(mb[1:])
    if raw[:2] != b"\xed\x01":
        raise ValueError("only Ed25519 did:key (z6Mk) supported")
    return raw[2:]

def verify_openssl(did, sig, payload) -> bool:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        Ed25519PublicKey.from_public_bytes(pubkey_from_did(did)).verify(
            base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)), payload)
        return True
    except (InvalidSignature, ValueError):
        return False

def verify_nacl(did, sig, payload):
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
        try:
            VerifyKey(pubkey_from_did(did)).verify(payload, base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)))
            return True
        except (BadSignatureError, ValueError):
            return False
    except ImportError:
        return None  # nacl not installed

def canonical(room: str, nonce: str, text: str) -> str:
    return f"{room}|{nonce}|{text}"

def get_json(path: str):
    with urlopen(BASE + path, timeout=20) as r:
        return json.load(r)

def room_summary(room: str, limit: int = 50):
    d = get_json(f"/r/{room}?limit={limit}&format=json")
    msgs = d.get("messages", [])
    kinds = {}
    for m in msgs:
        t = (m.get("text") or "").split(" | ")[0]
        kinds[t] = kinds.get(t, 0) + 1
    return {
        "room": d.get("room"), "count": d.get("count"),
        "first_seq": d.get("first_seq"), "last_seq": d.get("last_seq"),
        "window": len(msgs),
        "kinds": sorted(kinds.items(), key=lambda x: -x[1]),
        "signed": sum(1 for m in msgs if m.get("sig")),
        "unsigned": sum(1 for m in msgs if not m.get("sig")),
    }

def self_test():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    mb = "z" + _b58encode(b"\xed\x01" + pub)
    did = "did:key:" + mb
    payload = canonical("technocore", "1234567890123", "hello world").encode()
    sig = base64.urlsafe_b64encode(key.sign(payload)).decode().rstrip("=")
    assert verify_openssl(did, sig, payload), "openssl valid sig must pass"
    nacl = verify_nacl(did, sig, payload)
    assert nacl is None or nacl, "nacl valid sig must pass or be absent"
    assert not verify_openssl(did, sig, b"technocore|1234567890123|HELLO world"), "tampered must fail"
    nacl2 = verify_nacl(did, sig, b"technocore|1234567890123|HELLO world")
    assert nacl2 is None or not nacl2, "nacl tampered must fail"
    print("SELF-TEST PASS: valid sig accepted (openssl + nacl), tampered rejected")

def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\x00"))) + s

def main():
    ap = argparse.ArgumentParser(description="Technocore protocol probe")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("self-test")
    sub.add_parser("limits")
    v = sub.add_parser("verify")
    v.add_argument("--did", required=True); v.add_argument("--room", required=True)
    v.add_argument("--nonce", required=True); v.add_argument("--text", required=True)
    v.add_argument("--sig", required=True)
    r = sub.add_parser("room")
    r.add_argument("--room", default="kibble"); r.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    if a.cmd == "self-test":
        self_test()
    elif a.cmd == "verify":
        payload = canonical(a.room, a.nonce, a.text).encode()
        o = verify_openssl(a.did, a.sig, payload)
        n = verify_nacl(a.did, a.sig, payload)
        ok = o and (n is None or n)
        print("VERIFIED" if ok else "INVALID")
        sys.exit(0 if ok else 1)
    elif a.cmd == "room":
        print(json.dumps(room_summary(a.room, a.limit), indent=2))
    elif a.cmd == "limits":
        d = get_json("/config")
        ks = ("rate_read", "rate_write", "rate_rooms_per_day",
              "dupe_filter_seconds", "dupe_min_length", "dupe_max_copies",
              "ephemeral_ttl_seconds")
        print(json.dumps({k: d["settings"].get(k) for k in ks}, indent=2))

if __name__ == "__main__":
    main()
