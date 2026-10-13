#!/usr/bin/env python3
"""Package CI-built binaries into a customer ZIP without source/GitHub access."""
import argparse
import hashlib
from pathlib import Path
import stat
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('artifacts', type=Path)
parser.add_argument('--source', required=True, help='Source Git commit')
parser.add_argument('--output', type=Path, default=Path('public/downloads/I-KNOW-WHAT-I-SAW.zip'))
args = parser.parse_args()
files = {
 'Windows/iknowwhatisaw.exe': args.artifacts/'pc/windows/iknowwhatisaw.exe',
 'Windows/SDL2.dll': args.artifacts/'pc/windows/SDL2.dll',
 'Linux/iknowwhatisaw': args.artifacts/'pc/linux/iknowwhatisaw',
 'Linux/lib/libSDL2-2.0.so.0': args.artifacts/'pc/linux/lib/libSDL2-2.0.so.0',
 'Linux/run.sh': args.artifacts/'pc/linux/run.sh',
 'ESP32-C3/I-KNOW-WHAT-I-SAW-ESP32-C3.bin': args.artifacts/'esp32-c3/I-KNOW-WHAT-I-SAW-ESP32-C3.bin',
}
for p in files.values():
    if not p.is_file() or not p.stat().st_size: raise SystemExit('Missing build artifact: '+str(p))
readme = '''I KNOW WHAT I SAW — Windows, Linux and ESP32-C3

Extract this entire folder before playing. No GitHub account or source checkout is needed.

WINDOWS (64-bit): Open Windows/iknowwhatisaw.exe.
Keep SDL2.dll next to the EXE. This independent release is not code signed.

LINUX (64-bit x86): In Linux/, run chmod +x run.sh iknowwhatisaw, then ./run.sh.
SDL2 is included in lib/. Built on Ubuntu 22.04; requires glibc 2.35+ and
normal desktop graphics/audio libraries. Not an ARM/Raspberry Pi build.

CONTROLS: Arrows/WASD move; Z/Space = A; X = B; Enter = START;
Esc = menu; F11/Alt+Enter = fullscreen. USB gamepads supported.
Saves: Windows %APPDATA%/Weeks/I Know What I Saw/
       Linux ~/.local/share/Weeks/I Know What I Saw/

ESP32-C3 HANDHELD: Firmware in ESP32-C3/ targets ONLY the ESP32-C3 Super Mini
with the wiring described in ESP32-C3/README.txt. It is not a generic ESP32
or ESP32-S3 build. Hardware playback has not been verified.

Follow each platform's instructions. Do not copy this PC game to an X16 SD card.
'''
esp = '''I KNOW WHAT I SAW — ESP32-C3 Super Mini firmware

Merged firmware includes bootloader, partition table and game; flash at 0x0.
Built with ESP-IDF 5.4.4. Only flash to an ESP32-C3 with this exact peripheral wiring.
Hardware is not yet tested. Back up existing firmware/saves before flashing;
flashing replaces the firmware on the device. No erase-flash step is required.

Install Python 3 and esptool:
  python -m pip install "esptool>=4.8,<5"
Put the C3 into USB download mode (hold BOOT, tap RESET, release BOOT).
Windows example (replace COM3 with your device's port):
  py -m esptool --chip esp32c3 --port COM3 --baud 460800 write_flash 0x0 I-KNOW-WHAT-I-SAW-ESP32-C3.bin
Linux example (replace the port as needed):
  python3 -m esptool --chip esp32c3 --port /dev/ttyACM0 --baud 460800 write_flash 0x0 I-KNOW-WHAT-I-SAW-ESP32-C3.bin
Reset after flashing. A+B together acts as START.

Display: 1.69-inch ST7789 240x280 SPI; SCL GPIO4, SDA/MOSI GPIO6,
RES GPIO7, DC GPIO2, CS GPIO10, BLK 3V3.
Buttons: PCF8574 address 0x20, SDA GPIO8, SCL GPIO9.
P0 up, P1 down, P2 left, P3 right, P4 A, P5 B, P6 optional START.
Audio MAX98357A: BCLK GPIO21, LRC GPIO0, DIN GPIO20, SD GPIO5, GAIN unconnected.
Vibration IN GPIO3; IR TX GPIO1. UART0 pins 20/21 are used for audio;
logs use native USB. GPIO2/8/9 are strapping pins; do not add pull-downs.
Display orientation/colour order may need a custom firmware build for other panels.
'''
extra = {'README.txt': readme.encode(), 'ESP32-C3/README.txt': esp.encode(),
         'BUILD.txt': ('Source commit: '+args.source+'\nBuild: Windows/Linux Ubuntu22.04 CI; ESP-IDF5.4.4 ESP32-C3\n').encode(),
         'SDL2-LICENSE.txt': (args.artifacts/'SDL2-LICENSE.txt').read_bytes()}
checks=[]
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for name, data in sorted({**{n:p.read_bytes() for n,p in files.items()}, **extra}.items()):
        info=zipfile.ZipInfo('I-KNOW-WHAT-I-SAW/'+name, date_time=(2026,10,13,0,0,0))
        info.create_system=3
        info.external_attr=(stat.S_IFREG | (0o755 if name in ['Linux/run.sh','Linux/iknowwhatisaw'] else 0o644)) << 16
        archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED)
        checks.append(hashlib.sha256(data).hexdigest()+'  '+name)
    archive.writestr('I-KNOW-WHAT-I-SAW/SHA256SUMS.txt','\n'.join(checks)+'\n')
print(args.output, args.output.stat().st_size, hashlib.sha256(args.output.read_bytes()).hexdigest())
