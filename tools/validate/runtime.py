"""Explicit Windows own-process UI QA. No original-install writes or game cheats.

Screenshots/exit status are evidence, not an automatic visual acceptance verdict.
Requires a complete isolated game copy; --game-dir is the immutable source.
"""

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from PIL import ImageGrab

MATRIX = [(1366, 768), (1920, 1080), (2560, 1440), (3840, 2160)]


def run(game, runtime, build, out, size, view, original=False):
    game, runtime, build, out = (p.resolve() for p in (game, runtime, build, out))
    if runtime == game or runtime.is_relative_to(game):
        raise ValueError("Runtime must be outside the original game")
    if size not in MATRIX:
        raise ValueError("QA resolutions: 1366x768, 1920x1080, 2560x1440, 3840x2160")
    if not (runtime / "System/WoT.exe").is_file():
        raise ValueError("Provide a complete separate runtime copy")
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((build / "BUILD_REPORT.json").read_text("utf8"))
    for name, hashes in report["files"].items():
        b = (game / name).read_bytes()
        if hashlib.sha256(b).hexdigest() != hashes["original_sha256"]:
            raise ValueError("Original fingerprint changed")
        source = game / name if original else build / "resources" / name
        shutil.copyfile(source, runtime / name)
    for n in ("WoT.ini", "User.ini"):
        shutil.copyfile(game / "System" / n, runtime / "System" / n)
    ini = runtime / "System/WoT.ini"
    text = ini.read_bytes().decode("cp1252")
    for field, value in [
        ("FullscreenViewportX", size[0]),
        ("WindowedViewportX", size[0]),
        ("FullscreenViewportY", size[1]),
        ("WindowedViewportY", size[1]),
    ]:
        text, count = re.subn(
            r"(?m)^" + field + r"=\d+", field + "=" + str(value), text
        )
        if not count:
            raise ValueError("Missing viewport setting: " + field)
    ini.write_bytes(text.encode("cp1252"))
    user = ctypes.windll.user32
    user.GetForegroundWindow.restype = ctypes.c_void_p
    user.SetProcessDPIAware()
    callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def windows(pid):
        items = []

        def cb(handle, _):
            owner = ctypes.c_ulong()
            user.GetWindowThreadProcessId(ctypes.c_void_p(handle), ctypes.byref(owner))
            if owner.value == pid and user.IsWindowVisible(ctypes.c_void_p(handle)):
                title = ctypes.create_unicode_buffer(512)
                user.GetWindowTextW(ctypes.c_void_p(handle), title, 512)
                items.append((handle, title.value))
            return True

        user.EnumWindows(callback(cb), 0)
        return items

    level = {"menu": "Entry", "inventory": "Mission_01", "subtitle": "Tutorial"}[view]
    command = [".\\WoT.exe", level] + ([] if view == "subtitle" else ["-nosound"])
    old_cwd = Path.cwd()
    os.chdir(runtime / "System")
    proc = subprocess.Popen(command)
    started = time.monotonic()
    result = {
        "requested": list(size),
        "view": view,
        "original": original,
        "command": command,
        "resource_sha256": {
            n: hashlib.sha256((runtime / n).read_bytes()).hexdigest()
            for n in report["files"]
        },
        "input": [],
        "screenshots": [],
        "error": None,
        "visual_review": "pending",
    }
    label = ("original" if original else "modified") + f"_{size[0]}x{size[1]}_{view}"
    try:
        handle = None
        for _ in range(60):
            handle = next(
                (h for h, title in windows(proc.pid) if title == "Wheel of Time"), None
            )
            if handle:
                user.ShowWindow(ctypes.c_void_p(handle), 9)
                user.SetForegroundWindow(ctypes.c_void_p(handle))
                break
            if proc.poll() is not None:
                raise RuntimeError("Exited before game window")
            time.sleep(0.2)
        if not handle:
            raise RuntimeError("Game window absent")

        def capture(tag):
            rect = (ctypes.c_long * 4)()
            user.GetWindowRect(ctypes.c_void_p(handle), rect)
            image = ImageGrab.grab(bbox=tuple(rect))
            path = out / (label + "_" + tag + ".png")
            image.save(path)
            result["screenshots"].append(
                {
                    "file": path.name,
                    "seconds": round(time.monotonic() - started, 2),
                    "window_rect": list(rect),
                    "image_size": list(image.size),
                }
            )
            if all(hi - lo < 3 for lo, hi in image.convert("RGB").getextrema()):
                raise RuntimeError("Uniform frame is not a verified UI result")

        if view == "subtitle":
            for when in (10, 20, 25, 36):
                time.sleep(max(0, when - (time.monotonic() - started)))
                capture(str(when))
        else:
            time.sleep(max(0, 13 - (time.monotonic() - started)))
            user.SetForegroundWindow(ctypes.c_void_p(handle))
            keys = [27, 13] if view == "menu" else [114, 49, 113]
            result["input"] = (
                ["Escape", "Enter"]
                if view == "menu"
                else ["F3", "1", "F2", "wait 10s for precache"]
            )
            for key in keys:
                if user.GetForegroundWindow() != handle:
                    raise RuntimeError("Own game window lost foreground; no key sent")
                user.keybd_event(key, 0, 0, 0)
                time.sleep(0.1)
                user.keybd_event(key, 0, 2, 0)
                time.sleep(2)
            if view == "inventory":
                time.sleep(10)
            capture("settled")
    except Exception as exc:
        result["error"] = repr(exc)
    finally:
        owned = windows(proc.pid)
        main_window = next((h for h, title in owned if title == "Wheel of Time"), None)
        # Do not close the DirectDraw proxy before the main viewport tears down.
        closing = [(main_window, "Wheel of Time")] if main_window else owned
        for h, title in closing:
            user.PostMessageW(ctypes.c_void_p(h), 0x10, 0, 0)
        try:
            result["exit_code"] = proc.wait(timeout=12)
            result["exit_method"] = "normal_exit"
        except subprocess.TimeoutExpired:
            proc.terminate()
            result["exit_code"] = proc.wait()
            result["exit_method"] = "terminated"
        log = (runtime / "System/WoT.log").read_bytes()
        (out / (label + ".log")).write_bytes(log)
        result["mode_log_lines"] = [
            line
            for line in log.decode("cp1252", errors="replace").splitlines()
            if re.search(
                r"best.?match|resolution|display mode|viewport|fullscreen", line, re.I
            )
        ]
        modes = re.findall(
            r"Best-match display mode: (\d+)x(\d+)x\d+",
            log.decode("cp1252", errors="replace"),
        )
        result["actual_modes"] = [list(map(int, mode)) for mode in modes]
        if list(size) not in result["actual_modes"] and not result["error"]:
            result["error"] = "Requested internal resolution not observed in native log"
        (out / (label + ".json")).write_text(json.dumps(result, indent=2), "utf8")
        os.chdir(old_cwd)
        print(
            f'RUNTIME {"PASS" if not result["error"] and result["exit_code"] == 0 else "FAIL"}: '
            f'{label}; native_exit={result["exit_code"]}; visual_review=pending',
            flush=True,
        )
    if result["error"] or result["exit_code"] != 0:
        raise RuntimeError("Runtime probe failed; inspect saved log/JSON")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("game-dir", "runtime-dir", "build-dir", "out"):
        p.add_argument("--" + option, type=Path, required=True)
    p.add_argument(
        "--resolution", required=True, choices=[f"{w}x{h}" for w, h in MATRIX]
    )
    p.add_argument("--view", choices=["menu", "inventory", "subtitle"], default="menu")
    p.add_argument("--original", action="store_true")
    a = p.parse_args()
    run(
        a.game_dir,
        a.runtime_dir,
        a.build_dir,
        a.out,
        tuple(map(int, a.resolution.split("x"))),
        a.view,
        a.original,
    )
