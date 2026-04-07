#!/bin/bash
# Auto-set best HDMI resolution
sleep 3
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000

# Get current preferred mode
CURRENT=

# If 800x480 is current but 1080p is available, switch to 1080p
if echo "" | grep -q "800x480"; then
    MODES=
    if [ -n "" ]; then
        wlr-randr --output HDMI-A-1 --mode 1920x1080@60 2>/dev/null
        echo "Switched to 1080p"
    fi
fi
