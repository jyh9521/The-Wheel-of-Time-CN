"""Language-neutral active QA policy and an offline probe plan; never launches a game."""

import argparse
import json
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parents[2] / "profiles/qa-policy.json"


def load_policy(path=POLICY_PATH):
    policy = json.loads(path.read_text("utf8"))
    active = [tuple(size) for size in policy["active_resolutions"]]
    excluded = {tuple(size) for size in policy["known_issue_resolutions"]}
    minimum = tuple(policy["minimum"])
    if len(active) != len(set(active)) or set(active) & excluded:
        raise ValueError("QA resolution sets overlap or contain duplicates")
    if tuple(policy["recommended"]) not in active:
        raise ValueError("Recommended resolution must be active")
    if any(
        len(size) != 2 or size[0] < minimum[0] or size[1] < minimum[1]
        for size in active
    ):
        raise ValueError("Active resolution is below the minimum")
    for view, count in policy.get("menu_item_counts", {}).items():
        if (
            view not in policy["views"]
            or type(count) is not int
            or not 1 <= count <= 64
        ):
            raise ValueError("Invalid menu sweep configuration")
    return policy


def sweep_count(policy, view, enabled):
    if not enabled:
        return 1
    if view not in policy.get("menu_item_counts", {}):
        raise ValueError("View has no configured read-only menu sweep")
    count = policy["menu_item_counts"][view]
    if type(count) is not int or not 1 <= count <= 64:
        raise ValueError("Invalid menu sweep configuration")
    return count


def make_plan(policy, locale):
    if not locale or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in locale
    ):
        raise ValueError("Invalid locale identifier")
    recommended = policy["recommended"]
    sizes = [recommended] + [
        s for s in policy["active_resolutions"] if s != recommended
    ]
    probes = []
    for size in sizes:
        for view in policy["views"]:
            for original in (True, False):
                args = [
                    "python",
                    "-m",
                    "tools.validate.runtime",
                    "--game-dir",
                    "GAME",
                    "--runtime-dir",
                    "build/runtime",
                    "--build-dir",
                    f"build/{locale}",
                    "--out",
                    "build/qa",
                    "--resolution",
                    f"{size[0]}x{size[1]}",
                    "--view",
                    view,
                ]
                if original:
                    args.append("--original")
                if view in policy.get("menu_item_counts", {}):
                    args.append("--sweep")
                probes.append(
                    {
                        "resolution": size,
                        "view": view,
                        "original": original,
                        "argv": args,
                    }
                )
    return {
        "locale": locale,
        "recommended": recommended,
        "launches_game": False,
        "probes": probes,
        "known_issue_resolutions": policy["known_issue_resolutions"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale", default="zh-CN")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plan = make_plan(load_policy(), args.locale)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2) + "\n", "utf8")
    print(
        f'QA PLAN PASS: {len(plan["probes"])} probes; recommended={plan["recommended"][0]}x{plan["recommended"][1]}; 4K excluded; no game launched'
    )
