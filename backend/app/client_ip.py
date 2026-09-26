"""Who is this caller? One answer for the rate limiter and the request log (BR-CACHE-004, AD-054).

Behind nginx or an Ingress the socket peer is a proxy. Trust `X-Forwarded-For` only when that
peer is a trusted proxy, and then take the LAST entry: the one the nearest trusted proxy
appended. The first entry is whatever the client sent, so keying on it lets any caller mint a
fresh quota with one forged header.
"""

from collections.abc import Sequence
from ipaddress import IPv4Network, IPv6Network, ip_address

UNKNOWN = "unknown"


def resolve_client_ip(
    peer: str | None,
    forwarded_for: str | None,
    trusted: Sequence[IPv4Network | IPv6Network],
) -> str:
    if peer is None:
        return UNKNOWN
    try:
        peer_ip = ip_address(peer)
    except ValueError:
        return peer  # e.g. the test client's "testclient"; still a stable per-caller key
    if not forwarded_for or not any(peer_ip in network for network in trusted):
        return str(peer_ip)
    last = forwarded_for.rsplit(",", 1)[-1].strip()
    try:
        return str(ip_address(last))
    except ValueError:
        # A trusted proxy never appends garbage; if it did, the peer is the honest answer.
        return str(peer_ip)
