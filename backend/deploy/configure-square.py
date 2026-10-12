#!/usr/bin/env python3
"""Run interactively on the droplet; secrets never enter shell history or chat."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["sandbox", "live"], default="sandbox")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run as root on the droplet.")
    token = getpass.getpass(f"Square {args.mode} access token (hidden): ").strip()
    location = input(f"Square {args.mode} location ID: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_+./=-]{20,1000}", token):
        parser.error("Invalid token format; nothing saved.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", location):
        parser.error("Invalid location ID; nothing saved.")
    path = Path("/etc/roddy-store/store.env")
    values = {
        "SQUARE_ACCESS_TOKEN": token,
        "SQUARE_LOCATION_ID": location,
        "SQUARE_MODE": args.mode,
        "STORE_DATABASE": f"/var/lib/roddy-store/orders-{args.mode}.sqlite3",
        "STORE_CHECKOUT_ENABLED": "true",
        "STORE_PRIVATE_DIR": "/var/lib/roddy-store/files",
        "STORE_MANIFEST": "/etc/roddy-store/digital-products.json",
    }
    if args.mode == "sandbox":
        # Public sandbox payments must never unlock the real paid release.
        folder = Path("/var/lib/roddy-store/sandbox-files")
        folder.mkdir(mode=0o750, exist_ok=True)
        shutil.chown(folder, user="root", group="roddystore")
        archive = folder / "DESK-COMMANDER-SANDBOX.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as test_zip:
            test_zip.writestr("SANDBOX-READ-ME.txt", "RODDY Store sandbox delivery test. No money was charged. This ZIP contains no paid software.\n")
        archive.chmod(0o640)
        shutil.chown(archive, user="root", group="roddystore")
        manifest = Path("/etc/roddy-store/sandbox-products.json")
        manifest.write_text(json.dumps({"desk-commander": {
            "file": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "sandbox": True,
        }}, indent=2) + "\n")
        manifest.chmod(0o640)
        shutil.chown(manifest, user="root", group="roddystore")
        values.update(STORE_PRIVATE_DIR=str(folder), STORE_MANIFEST=str(manifest))
    lines = path.read_text().splitlines()
    updated = []
    for line in lines:
        key = line.partition("=")[0]
        updated.append(key + "=" + values.pop(key) if key in values else line)
    updated.extend(key + "=" + value for key, value in values.items())
    path.write_text("\n".join(updated) + "\n")
    path.chmod(0o640)
    subprocess.run(["systemctl", "restart", "roddy-store"], check=True)
    print(f"Saved {args.mode} credentials and restarted only roddy-store.")
    print("Public storefront checkout stays disabled until its catalog setting is enabled.")


if __name__ == "__main__":
    main()
