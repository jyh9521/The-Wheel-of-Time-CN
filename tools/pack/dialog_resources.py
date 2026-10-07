"""Localize Windows dialog-template captions without changing control identities."""
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import struct


def transform(data, translations):
    extended = data[:4] == b'\x01\x00\xff\xff'
    header = 26 if extended else 18
    style = struct.unpack_from('<I', data, 12 if extended else 0)[0]
    count = struct.unpack_from('<H', data, 16 if extended else 8)[0]
    pos, out, changes = header, bytearray(data[:header]), []

    def field(translatable=False):
        nonlocal pos
        start = pos
        first = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        if first == 0xffff:
            pos += 2
            out.extend(data[start:pos])
            return
        while first:
            first = struct.unpack_from('<H', data, pos)[0]
            pos += 2
        value = data[start:pos-2].decode('utf-16le')
        replacement = translations.get(value, value) if translatable else value
        if replacement != value:
            if '\0' in replacement:
                raise ValueError('NUL in dialog caption')
            changes.append({'before': value, 'after': replacement})
        out.extend(replacement.encode('utf-16le') + b'\0\0')

    field(); field(); field(True)
    if style & 0x40:
        size = 6 if extended else 2
        out.extend(data[pos:pos+size]); pos += size
        field()  # Keep point size, weight, charset and font unchanged.
    for _ in range(count):
        pos = (pos+3) & ~3
        out.extend(b'\0' * ((-len(out)) % 4))
        size = 24 if extended else 18
        out.extend(data[pos:pos+size]); pos += size
        field(); field(True)
        extra = struct.unpack_from('<H', data, pos)[0]
        out.extend(data[pos:pos+2+extra]); pos += 2+extra
    out.extend(data[pos:])
    return bytes(out), changes


def patch(source, output, expected_sha256, dialogs):
    import pefile
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Dialog input fingerprint differs')
    if source.resolve() == output.resolve():
        raise ValueError('Dialog output must be a copy')
    pe = pefile.PE(data=data)
    updates, changes = [], []
    for kind in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if kind.id != 5:
            continue
        for item in kind.directory.entries:
            if str(item.id) not in dialogs:
                continue
            for lang in item.directory.entries:
                d=lang.data.struct
                original=pe.get_data(d.OffsetToData,d.Size)
                modified, rows=transform(original, dialogs[str(item.id)])
                restored,_=transform(modified,{r['after']:r['before'] for r in rows})
                if restored != original:
                    raise ValueError('Dialog round trip differs')
                updates.append((item.id,lang.id,modified))
                changes.extend({'dialog':item.id,'language':lang.id,**row} for row in rows)
    if set(str(i) for i,_,_ in updates) != set(dialogs):
        raise ValueError('Required dialogs missing')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(data)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.BeginUpdateResourceW.argtypes=[wintypes.LPCWSTR,wintypes.BOOL]
    kernel.BeginUpdateResourceW.restype=wintypes.HANDLE
    kernel.UpdateResourceW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,wintypes.WORD,ctypes.c_void_p,wintypes.DWORD]
    kernel.UpdateResourceW.restype=wintypes.BOOL
    kernel.EndUpdateResourceW.argtypes=[wintypes.HANDLE,wintypes.BOOL]
    kernel.EndUpdateResourceW.restype=wintypes.BOOL
    handle=kernel.BeginUpdateResourceW(str(output.resolve()),False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    committed=False
    try:
        for ident,language,blob in updates:
            buffer=ctypes.create_string_buffer(blob)
            if not kernel.UpdateResourceW(handle,5,ident,language,buffer,len(blob)):
                raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.EndUpdateResourceW(handle,False):
            raise ctypes.WinError(ctypes.get_last_error())
        committed=True
    finally:
        if not committed:
            kernel.EndUpdateResourceW(handle,True)
    new=pefile.PE(str(output))
    # UpdateResource compacts .rsrc and may move the appended .locale section.
    # That would invalidate absolute/RVA references in the existing display
    # adaptation. Reserve unused resource space so later section RVAs stay put.
    old_resource=next(s for s in pe.sections if s.Name.startswith(b'.rsrc'))
    new_resource=next(s for s in new.sections if s.Name.startswith(b'.rsrc'))
    if any(next((n for n in new.sections if n.Name==s.Name),s).VirtualAddress!=s.VirtualAddress
           for s in pe.sections if not s.Name.startswith(b'.rsrc')):
        padding=old_resource.Misc_VirtualSize-new_resource.Misc_VirtualSize+128
        if padding<=0:
            raise ValueError('Resource growth would move runtime section')
        new.close()
        handle=kernel.BeginUpdateResourceW(str(output.resolve()),False)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        buffer=ctypes.create_string_buffer(b'\0'*padding)
        if not kernel.UpdateResourceW(handle,10,65000,1033,buffer,padding):
            kernel.EndUpdateResourceW(handle,True)
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.EndUpdateResourceW(handle,False):raise ctypes.WinError(ctypes.get_last_error())
        new=pefile.PE(str(output))
    for section in pe.sections:
        if section.Name.startswith(b'.rsrc'):
            continue
        match=next((s for s in new.sections if s.Name==section.Name),None)
        if match is None or match.VirtualAddress!=section.VirtualAddress or match.get_data()!=section.get_data():
            raise ValueError('Non-resource section changed: '+str(section.Name))
    observed={}
    for kind in new.DIRECTORY_ENTRY_RESOURCE.entries:
        for item in kind.directory.entries:
            for lang in item.directory.entries:
                key=(kind.id,item.id,lang.id);d=lang.data.struct
                observed[key]=new.get_data(d.OffsetToData,d.Size)
    for ident,lang,blob in updates:
        if observed[(5,ident,lang)]!=blob:
            raise ValueError('Dialog readback differs')
    for kind in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        for item in kind.directory.entries:
            for lang in item.directory.entries:
                key=(kind.id,item.id,lang.id);d=lang.data.struct
                if (kind.id != 5 or str(item.id) not in dialogs) and observed[key]!=pe.get_data(d.OffsetToData,d.Size):
                    raise ValueError('Unrelated resource changed')
    return {'field':'RT_DIALOG captions only','source_sha256':expected_sha256,
            'modified_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'changes':changes,'non_resource_sections_unchanged':True,'unrelated_resources_unchanged':True,
            'font_metrics_and_control_ids_unchanged':True,'in_game_verified':False}
