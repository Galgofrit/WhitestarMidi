#!/usr/bin/env python3
"""Push, list, or read files on the Whitestar Pico in WiFi mode.

Defaults to whitestar.local. Override with --host <ip-or-name>.

Usage:
    ./push.py <file> [<file> ...]         # upload files
    ./push.py --reset                     # restart the device
    ./push.py --ls [path]                 # list files
    ./push.py --cat <path>                # print file contents
    ./push.py --host <ip> <file> ...      # use a specific host
"""
import socket
import sys
import os

PORT = 8080
DEFAULT_HOST = "whitestar.local"

def send(host, payload, all_data=False):
    with socket.create_connection((host, PORT), timeout=10) as s:
        s.sendall(payload)
        if all_data:
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks).decode()
        return s.recv(4096).decode().strip()

def push(host, path):
    name = os.path.basename(path)
    with open(path, "rb") as f:
        data = f.read()
    header = f"PUT {name}\n{len(data)}\n".encode()
    print(f"{name}: {send(host, header + data)}")

if __name__ == "__main__":
    args = sys.argv[1:]
    host = DEFAULT_HOST
    if args and args[0] == "--host":
        if len(args) < 2:
            print(__doc__)
            sys.exit(1)
        host = args[1]
        args = args[2:]

    if not args:
        print(__doc__)
        sys.exit(1)

    op = args[0]
    if op == "--reset" or op == "--restart":
        print(send(host, b"RST\n\n"))
    elif op == "--ls":
        path = args[1] if len(args) > 1 else "/"
        print(send(host, f"LS {path}\n\n".encode(), all_data=True))
    elif op == "--cat":
        print(send(host, f"CAT {args[1]}\n\n".encode(), all_data=True))
    else:
        for f in args:
            push(host, f)
