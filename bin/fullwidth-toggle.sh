#!/usr/bin/env bash
# Toggle focused column full-width, tracked per window address
# Restores to DEFAULT_WIDTH when toggled off

DEFAULT_WIDTH="0.5"  # Change this to match your scrolling:column_width setting
STATE_DIR="/tmp/hypr_fullcol"
mkdir -p "$STATE_DIR"

ADDR=$(hyprctl activewindow -j | jq -r '.address')

if [ -z "$ADDR" ] || [ "$ADDR" = "null" ]; then
    exit 1
fi

STATE_FILE="$STATE_DIR/$ADDR"

if [ -f "$STATE_FILE" ]; then
    hyprctl dispatch layoutmsg "colresize $DEFAULT_WIDTH"
    hyprctl dispatch layoutmsg "move -col"

    rm "$STATE_FILE"
else
    hyprctl dispatch layoutmsg "colresize 1.0"
    touch "$STATE_FILE"
fi
