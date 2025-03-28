#!/bin/bash

echo "🌎 Setting timezone to America/New_York"
ln -snf /usr/share/zoneinfo/America/New_York /etc/localtime
echo "America/New_York" > /etc/timezone

echo "👋 Starting FocusFlag Add-on"
echo "📎 Listing USB Devices:"
lsusb || echo "⚠️ lsusb not available"

echo "🔍 Bus info (Expecting Luxafor at ID 04d8:f372):"
lsusb -v -d 04d8:f372 2>/dev/null || echo "❌ Luxafor not found (ID 04d8:f372)"

echo "🧪 Checking USB access via pyusb:"
python3 -c "
import usb.backend.libusb1, usb.core
backend = usb.backend.libusb1.get_backend(find_library=lambda x: '/usr/lib/libusb-1.0.so')
dev = usb.core.find(idVendor=0x04D8, idProduct=0xF372, backend=backend)
print('🎉 Luxafor device detected:', dev) if dev else print('❌ pyusb could not detect Luxafor')
"

echo "🚀 Launching FocusFlag API..."
python3 focusflag_api.py

# Made with ❤️ for focus and flow
