#!/usr/bin/env bash
INTERFACE="ppp0"

if ip link show "$INTERFACE" >/dev/null 2>&1; then
    IP=$(ip -4 addr show "$INTERFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    # Connected → lock
    echo "{\"text\":\"🔐\",\"tooltip\":\"VPN Connected\n$IP\"}"
else
    # Disconnected → globe
    echo "{\"text\":\"🌐\",\"tooltip\":\"VPN Disconnected\"}"
fi
