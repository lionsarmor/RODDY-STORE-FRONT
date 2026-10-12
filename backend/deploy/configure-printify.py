#!/usr/bin/env python3
"""Connect Printify without putting its token in GitHub, shell history, or chat."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.printify import Printify, PrintifyUnavailable


def save_connection(path, data):
    # Write atomically with private permissions from the instant of creation.
    descriptor, temporary = tempfile.mkstemp(prefix=".printify-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            json.dump(data, output)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        shutil.chown(temporary, user="root", group="roddystore")
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run this command as root in the droplet console.")
    token = getpass.getpass("Printify API token (hidden): ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_+./=-]{20,4000}", token):
        parser.error("Invalid token format. Nothing saved.")
    try:
        client = Printify(token)
        shops = client.shops()
        if not shops:
            parser.error("Create a RODDY API store in Printify, then rerun this command. Nothing saved.")
        for number, shop in enumerate(shops, 1):
            print(f"{number}. {shop['title']} ({shop['id']}; {shop['channel']})")
        if len(shops) == 1:
            selected = shops[0]
        else:
            try:
                number = int(input("Choose the RODDY API store number: "))
                if not 1 <= number <= len(shops):
                    raise ValueError()
                selected = shops[number - 1]
            except ValueError:
                parser.error("Invalid store number. Nothing saved.")
        client.shop_id = selected["id"]
        inventory = client.products()  # Verify products.read before saving anything.
        save_connection(Path("/etc/roddy-store/printify.json"), {"token": token, "shopId": selected["id"]})
        print(f"Connected Printify store: {selected['title']} ({selected['id']}).")
        print(f"Products on first page: {len(inventory['products'])}.")
        print("Open RODDY admin > Printify merchandise > Check connection & load products.")
        print("Merchandise ordering is not enabled. No orders were created or charged.")
    except PrintifyUnavailable as exc:
        parser.error(str(exc) + " Nothing saved.")


if __name__ == "__main__":
    main()
