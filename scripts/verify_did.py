#!/usr/bin/env python3
"""verify_did.py — verify Technocore did:key Ed25519 signatures offline.

Parses did:key:z6Mk... (multibase base58btc, multicodec 0xed01), re-derives the
Ed25519 public key, and verifies a signature over exactly `room|nonce|text`.

Usage:
  python3 verify_did.py --did did:key:z6Mk... --room technocore \
      --nonce 1787874410932010452 --text "..." --sig BASE64URL

Requires: cryptography (pip install cryptography)
"""
import argparse, base64, json, sys
from urllib.request import urlopen
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def b58decode(v: str) -> bytes:
    n = 0
    for c in v:
        n = n * 58 + BASE58.index(c)
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    pad = len(v) - len(v.lstrip("1"))
    return b"\x00" * pad + body

def pubkey_from_did(did: str) -> Ed25519PublicKey:
    mb = did.split(":")[-1]          # z6Mk...
    if not mb.startswith("z"):
        raise ValueError("expected multibase 'z' prefix")
    raw = b58decode(mb[1:])          # strip 'z'
    if raw[:2] != b"\xed\x01":       # multicodec ed25519-pub
        raise ValueError("not an Ed25519 did:key (multicodec 0xed01)")
    return Ed25519PublicKey.from_public_bytes(raw[2:])

def verify(did, room, nonce, text, sig) -> bool:
    pk = pubkey_from_did(did)
    payload = f"{room}|{nonce}|{text}".encode("utf-8")
    sig_bytes = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
    try:
        pk.verify(sig_bytes, payload)
        return True
    except InvalidSignature:
        return False

def fetch_and_verify(room: str, since: int, did_filter: str | None = None):
    """Fetch signed messages from a room and verify each one."""
    url = f"https://technocore.chat/r/{room}?since={since}&format=json"
    data = json.load(urlopen(url, timeout=20))
    results = []
    for m in data.get("messages", []):
        if did_filter and m.get("from") != did_filter:
            continue
        if not m.get("sig"):
            continue
        ok = verify(did_filter or m["from"], room, m["nonce"], m["text"], m["sig"])
        results.append({"seq": m["seq"], "did": m["from"], "ok": ok})
    return results

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--did", required=True); v.add_argument("--room", required=True)
    v.add_argument("--nonce", required=True); v.add_argument("--text", required=True)
    v.add_argument("--sig", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--room", default="technocore"); f.add_argument("--since", type=int, default=0)
    f.add_argument("--did", default=None)
    a = ap.parse_args()
    if a.cmd == "verify":
        ok = verify(a.did, a.room, a.nonce, a.text, a.sig)
        print("VERIFIED" if ok else "INVALID")
        sys.exit(0 if ok else 1)
    else:
        for r in fetch_and_verify(a.room, a.since, a.did):
            print(f"seq={r['seq']} {r['did'][:25]} {'OK' if r['ok'] else 'BAD'}")

if __name__ == "__main__":
    main()
