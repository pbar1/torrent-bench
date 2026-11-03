#!/bin/sh
# Transmission 4.1 probes its source IP with connect() on a UDP socket to this
# hardcoded address. connect() sends no packet, but fails without a matching
# route. A link-only /32 lets source selection succeed in Docker's internal
# network. There is still no default route, gateway, or internet egress.
if ! ip route show default | grep -q '^default'; then
    ip route add 91.121.74.28/32 dev eth0
fi
