#!/usr/bin/env bash

INTERFACE="ppp0"
SERVICE="openfortivpn.service"

# Disconnect
if ip link show "$INTERFACE" >/dev/null 2>&1; then
    systemctl --user stop "$SERVICE"
    notify-send "VPN" "Disconnected"
    exit 0
fi

# Ask OTP
OTP=$(walker -p "Forti Token" -x)  # -x biar input tersembunyi
[ -z "$OTP" ] && exit 1

systemctl --user set-environment VPN_OTP="$OTP"
systemctl --user set-environment SUDO_PASS="bismillah"
systemctl --user start "$SERVICE"

# Background check until interface appears
(
    for i in {1..20}; do
        sleep 1
        if ip link show "$INTERFACE" >/dev/null 2>&1; then
            notify-send "VPN" "Connected" 
            exit 0
        fi
    done
    notify-send "VPN" "Connection failed"
) &
