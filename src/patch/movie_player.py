"""Hash-gated, three-byte PlayMovie text selector experiment, not a release patch."""
import hashlib
import pefile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patch(data, profile):
    if len(data) != profile["size"] or sha(data) != profile["sha256"]:
        raise ValueError("Unknown WinDrv.dll version: size/SHA-256 mismatch")
    pe = pefile.PE(data=data)
    try:
        offset = pe.get_offset_from_rva(profile["rva"])
    finally:
        pe.close()
    before, after = bytes.fromhex(profile["before"]), bytes.fromhex(profile["after"])
    if len(before) != len(after) or data[offset:offset+len(before)] != before:
        raise ValueError("Unexpected PlayMovie selector bytes")
    result = data[:offset]+after+data[offset+len(before):]
    manifest = dict(source_sha256=sha(data), output_sha256=sha(result), size=len(data),
                    rva=profile["rva"], offset=offset, before=before.hex(),after=after.hex(),
                    field="PlayMovie text-track ordinal only", audio_path_unchanged=True)
    return result, manifest


def restore(data, manifest):
    if len(data)!=manifest["size"] or sha(data)!=manifest["output_sha256"]:
        raise ValueError("Modified WinDrv.dll SHA-256 mismatch")
    offset=manifest["offset"]
    before,after=bytes.fromhex(manifest["before"]),bytes.fromhex(manifest["after"])
    if len(before)!=len(after) or data[offset:offset+len(after)]!=after:
        raise ValueError("Rollback selector bytes mismatch")
    result=data[:offset]+before+data[offset+len(after):]
    if sha(result)!=manifest["source_sha256"]:
        raise ValueError("Restored WinDrv.dll SHA-256 mismatch")
    return result
