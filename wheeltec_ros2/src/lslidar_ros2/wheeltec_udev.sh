#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run: sudo $0"
    exit 1
fi

# Match the two WCH USB serial adapters by their hardware serial numbers.
# Change these values if the adapters are replaced.
FRONT_SERIAL="0002"
REAR_SERIAL="5B8E671812"
RULE_FILE="/etc/udev/rules.d/99-lslidar.rules"

cat > "${RULE_FILE}" <<EOF
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d4", ATTRS{serial}=="${FRONT_SERIAL}", GROUP="dialout", MODE="0660", SYMLINK+="lidar_front"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d4", ATTRS{serial}=="${REAR_SERIAL}", GROUP="dialout", MODE="0660", SYMLINK+="lidar_rear"
EOF

udevadm control --reload-rules
udevadm trigger

echo "Installed ${RULE_FILE}"
echo "Unplug and reconnect both lidars, then check:"
echo "  ls -l /dev/lidar_front /dev/lidar_rear"
