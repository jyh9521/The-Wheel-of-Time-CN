"""Version-specific native property display adapter, with locale-neutral tables.

Adds a position-independent read-only display lookup section to a copied DLL.
No configuration key, FName table, setter or property serializer is renamed.
"""
import json
import struct
from pathlib import Path
import pefile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
from src.patch.display_expressions import digest


def align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def assemble(source, address):
    return bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(source, address)[0])


def lookup(mapping, address):
    source = '''
        push ebx; push ecx; push edx; push esi; push edi;
        mov esi, eax;
        call anchor;
    anchor:
        pop ebx;
        lea edi, [ebx + 0x12345678];
    next:
        mov edx, [edi]; test edx, edx; jz fallback;
        add edx, ebx; mov ecx, esi;
    compare:
        mov ax, [ecx]; cmp ax, [edx]; jne miss;
        test ax, ax; jz found;
        add ecx, 2; add edx, 2; jmp compare;
    miss:
        add edi, 8; jmp next;
    found:
        mov eax, [edi + 4]; add eax, ebx; jmp finish;
    fallback:
        mov eax, esi;
    finish:
        pop edi; pop esi; pop edx; pop ecx; pop ebx; ret;
    '''
    code = bytearray(assemble(source, address))
    # Five register pushes, MOV ESI,EAX, then CALL with a zero displacement.
    anchor = 12
    if code[7:12] != b'\xe8\0\0\0\0':
        raise ValueError('Unexpected lookup assembler layout')
    table_offset = len(code)
    marker = struct.pack('<I', 0x12345678)
    if code.count(marker) != 1:
        raise ValueError('Lookup table relocation mismatch')
    start = code.index(marker)
    code[start:start + 4] = struct.pack('<i', table_offset - anchor)
    table = bytearray((len(mapping) + 1) * 8)
    strings = bytearray()
    for i, (key, translated) in enumerate(sorted(mapping.items())):
        if not key or not translated or '\0' in key + translated:
            raise ValueError('Invalid native display entry')
        offsets = []
        for text in (key, translated):
            offsets.append(table_offset + len(table) + len(strings) - anchor)
            strings += (text + '\0').encode('utf-16le')
        struct.pack_into('<ii', table, i * 8, *offsets)
    return bytes(code + table + strings)


def build(original, output, data_path, spec, report_path):
    source = original.read_bytes()
    if digest(source) != spec['sha256'] or len(source) != spec['size']:
        raise ValueError('Unsupported original Window.dll')
    config = data_path if isinstance(data_path, dict) else json.loads(Path(data_path).read_text('utf8'))
    if not 24 <= config['row_height'] <= 64 or not 200 <= config['minimum_divider_width'] <= 640:
        raise ValueError('Invalid native property layout metrics')
    pe = pefile.PE(data=source)
    if pe.FILE_HEADER.Machine != 0x14c or pe.OPTIONAL_HEADER.Magic != 0x10b:
        raise ValueError('Expected 32-bit PE')
    section_header = pe.sections[-1].get_file_offset() + 40
    if section_header + 40 > pe.OPTIONAL_HEADER.SizeOfHeaders or any(source[section_header:section_header + 40]):
        raise ValueError('No verified free PE section-header slot')
    base = pe.OPTIONAL_HEADER.ImageBase
    rva = align(pe.sections[-1].VirtualAddress + max(pe.sections[-1].Misc_VirtualSize, pe.sections[-1].SizeOfRawData), pe.OPTIONAL_HEADER.SectionAlignment)
    raw_offset = align(len(source), pe.OPTIONAL_HEADER.FileAlignment)
    payload = bytearray()
    label_lookup = rva
    payload += lookup(config['labels'], base + label_lookup)
    while len(payload) % 16:
        payload += b'\0'
    value_lookup = rva + len(payload)
    payload += lookup(config['values'], base + value_lookup)
    modified = bytearray(source)
    edits = []

    def patch(at, expected, replacement):
        off = pe.get_offset_from_rva(at)
        if modified[off:off + len(expected)] != expected or len(replacement) != len(expected):
            raise ValueError('Native display original bytes mismatch: ' + hex(at))
        modified[off:off + len(expected)] = replacement
        edits.append(dict(rva=at, expected_hex=expected.hex(), modified_hex=replacement.hex()))

    for name, at, expected in spec['caption_sites']:
        while len(payload) % 16:
            payload += b'\0'
        stub = rva + len(payload)
        tail = 'mov [ebp - 0x18], eax;' if name != 'property_draw' else 'push eax; push ecx;'
        payload += assemble(f'add eax, 12; call {base + label_lookup}; {tail} jmp {base + at + len(bytes.fromhex(expected))};', base + stub)
        size = len(bytes.fromhex(expected))
        patch(at, bytes.fromhex(expected), assemble(f'jmp {base + stub}', base + at) + b'\x90' * (size - 5))
    # Translate only the temporary value string in Draw(), not GetPropertyText
    # shared by setters, editors and config serialization.
    at = spec['value_draw_rva']
    while len(payload) % 16:
        payload += b'\0'
    stub = rva + len(payload)
    payload += assemble(f'''
        push eax; push ecx; push edx; push esi; push edi;
        lea eax, [ebp - 0x20b4];
        call {base + value_lookup};
        mov esi, eax; lea edi, [ebp - 0x20b4];
    copy_value:
        mov ax, [esi]; mov [edi], ax;
        add esi, 2; add edi, 2; test ax, ax; jnz copy_value;
        pop edi; pop esi; pop edx; pop ecx; pop eax;
        mov edx, [esi]; push edi; mov ecx, esi;
        jmp {base + at + 5};
    ''', base + stub)
    patch(at, bytes.fromhex(spec['value_draw_expected']), assemble(f'jmp {base + stub}', base + at))
    for at in spec['height_rvas']:
        patch(at, bytes.fromhex('b810000000'), b'\xb8' + struct.pack('<i', config['row_height']))
    while len(payload) % 16:
        payload += b'\0'
    divider = rva + len(payload)
    payload += assemble(f'''
        mov eax, [ecx + 0xc4]; cmp eax, {config['minimum_divider_width']}; jge done;
        mov eax, {config['minimum_divider_width']}; mov [ecx + 0xc4], eax;
    done: ret;
    ''', base + divider)
    patch(spec['divider_rva'], bytes.fromhex('8b81c4000000'), assemble(f'jmp {base + divider}', base + spec['divider_rva']) + b'\x90')
    raw_size = align(len(payload), pe.OPTIONAL_HEADER.FileAlignment)
    header = struct.pack('<8sIIIIIIHHI', b'.locale\0', len(payload), rva, raw_size, raw_offset, 0, 0, 0, 0, 0x60000020)
    modified[section_header:section_header + 40] = header
    struct.pack_into('<H', modified, pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'), pe.FILE_HEADER.NumberOfSections + 1)
    struct.pack_into('<I', modified, pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'), align(rva + len(payload), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I', modified, pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'), pe.OPTIONAL_HEADER.SizeOfCode + raw_size)
    struct.pack_into('<I', modified, pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'), 0)
    modified += b'\0' * (raw_offset - len(modified)) + payload + b'\0' * (raw_size - len(payload))
    allowed = set(range(section_header, section_header + 40))
    for edit in edits:
        off = pe.get_offset_from_rva(edit['rva'])
        allowed.update(range(off, off + len(bytes.fromhex(edit['expected_hex']))))
    for owner, field, size in [(pe.FILE_HEADER, 'NumberOfSections', 2),
                               (pe.OPTIONAL_HEADER, 'SizeOfImage', 4),
                               (pe.OPTIONAL_HEADER, 'SizeOfCode', 4),
                               (pe.OPTIONAL_HEADER, 'CheckSum', 4)]:
        off = owner.get_field_absolute_offset(field)
        allowed.update(range(off, off + size))
    if any(a != b and i not in allowed for i, (a, b) in enumerate(zip(source, modified))):
        raise ValueError('Native patch changed bytes outside approved display sites/PE fields')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(modified)
    rebuilt = pefile.PE(str(output))
    if rebuilt.sections[-1].Name != b'.locale\0' or rebuilt.get_data(rva, len(payload)) != payload:
        raise ValueError('Native section readback mismatch')
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        if rebuilt.get_data(entry.struct.FirstThunk, len(entry.imports) * 4) != pe.get_data(entry.struct.FirstThunk, len(entry.imports) * 4):
            raise ValueError('Native import table changed')
    report = dict(original_sha256=digest(source), modified_sha256=digest(bytes(modified)),
                  edits=edits, label_lookup_rva=label_lookup, value_lookup_rva=value_lookup,
                  labels=len(config['labels']), value_labels=len(config['values']),
                  row_height=config['row_height'], minimum_divider_width=config['minimum_divider_width'],
                  config_and_setter_code_unchanged=True, position_independent=True, in_game_verified=False)
    report['value_labels'] = len(config['values'])
    Path(report_path).write_text(json.dumps(report, indent=2) + '\n', 'utf8')
    print(f'NATIVE DISPLAY PASS: {len(config["labels"])} labels; {len(config["values"])} display values; row height {config["row_height"]}; minimum divider {config["minimum_divider_width"]}; import table unchanged')
    return report
