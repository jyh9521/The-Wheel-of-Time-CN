from fontTools.ttLib import TTFont


def check_font(rows, path, config):
    with TTFont(str(path), fontNumber=config.get("collection_index", 0)) as font:
        cmap = font.getBestCmap() or {}
        characters = {c for row in rows for c in row.get("translation", "")}
        characters.update(config["baseline_anchor"])
        missing = sorted(
            ord(c) for c in characters if not c.isspace() and ord(c) not in cmap
        )
        if missing:
            raise ValueError(
                "Missing glyphs: " + ", ".join(f"U+{c:04X}" for c in missing)
            )
    return characters
