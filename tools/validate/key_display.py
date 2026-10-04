"""Narrow bytecode/branch and binding-preservation checks for menuKeyboard.DrawValues."""

import argparse
import json
from pathlib import Path
from tools.pack.ue1 import Package, body, Reader
from src.patch.display_expressions import script_header


def check_vm(data):
    _, start, size = script_header(data)
    reader = Reader(data, start)
    vm, boundaries, targets = 0, set(), []

    def byte():
        nonlocal vm
        vm += 1
        return reader.u8()

    def expression():
        nonlocal vm
        boundaries.add(vm)
        op = byte()
        if op in (0, 1):
            reader.idx()
            vm += 4
        elif op in (15, 26):
            expression()
            expression()
        elif op in (6, 7):
            targets.append(int.from_bytes(data[reader.p : reader.p + 2], "little"))
            reader.p += 2
            vm += 2
            if op == 7:
                expression()
        elif op == 31:
            while byte():
                pass
        elif op in (37, 38, 39, 11):
            pass
        elif op == 36:
            byte()
        elif op == 27 or op >= 112:
            if op == 27:
                reader.idx()
                vm += 4
            while data[reader.p] != 22:
                expression()
            byte()
        elif op == 4:
            expression()
        else:
            raise ValueError("Unexpected profiled keyboard bytecode token")

    while vm < size:
        expression()
    if (
        vm != size
        or reader.p != len(data) - 7
        or any(t not in boundaries for t in targets)
    ):
        raise ValueError("Invalid keyboard VM size or jump target")
    return size, len(targets)


def verify(original_path, modified_path):
    old, new = Package(original_path), Package(modified_path)
    count = 0
    for record in old.records():
        if (
            not record["path"].startswith("menuKeyboard.")
            or record["class_name"] != "Function"
        ):
            continue
        original, modified = body(old, record["index"]), body(new, record["index"])
        if record["path"] == "menuKeyboard.DrawValues":
            if check_vm(original) != (229, 6) or check_vm(modified) != (295, 6):
                raise ValueError("Unexpected keyboard display script")
        elif original != modified:
            raise ValueError("Keyboard input/save function changed")
        count += 1
    print(
        f"KEY VM PASS: 295 VM bytes; 6 valid jumps; {count - 1} input/save functions unchanged"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--modified", type=Path, required=True)
    args = parser.parse_args()
    verify(args.original, args.modified)
