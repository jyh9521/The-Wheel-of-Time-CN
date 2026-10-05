"""GOG v68 native property editor limits; no locale data or engine setters."""
import struct
from src.patch.native_properties import assemble


def maximum_lookup(limits, address, names_iat):
    # ESI = FPropertyItem. Core exports verify UObject Outer=0x18, Name=0x20.
    # Return EAX=max or -1; preserve other registers. GNames is imported data.
    source = '''
        push ebx; push ecx; push edx; push edi;
        call anchor;
    anchor: pop ebx;
        mov ecx, [ebx + 0x12345678]; mov ecx, [ecx];
        mov edi, [esi + 0x3c]; test edi, edi; jz missing;
        mov edi, [edi + 0x18]; test edi, edi; jz missing;
        mov eax, [edi + 0x20]; mov eax, [ecx + eax * 4]; add eax, 12;
    '''
    # Owner and package guards avoid same-named unrelated properties.
    owners = {(x['package'], x['owner']) for x in limits}
    if len(owners) != 1 or any(x['minimum'] != 0 for x in limits):
        raise ValueError('This profiled editor supports one owner and zero-based integer limits')
    package, owner = next(iter(owners))
    for i, ch in enumerate(owner + '\0'):
        source += f'cmp word ptr [eax + {i*2}], {ord(ch)}; jne missing;'
    source += 'mov edi, [edi + 0x18]; test edi, edi; jz missing; mov eax, [edi + 0x20]; mov eax, [ecx + eax*4]; add eax, 12;'
    for i, ch in enumerate(package + '\0'):
        source += f'cmp word ptr [eax + {i*2}], {ord(ch)}; jne missing;'
    source += 'mov eax, [esi + 0x3c]; mov eax, [eax + 0x20]; mov edx, [ecx + eax*4]; add edx, 12;'
    for j, limit in enumerate(limits):
        if not 0 <= limit['maximum'] <= 4095:
            raise ValueError('Unexpected profiled integer limit')
        for i, ch in enumerate(limit['property'] + '\0'):
            source += f'cmp word ptr [edx + {i*2}], {ord(ch)}; jne next_{j};'
        source += f'mov eax, {limit["maximum"]}; jmp finish; next_{j}: '
    source += 'missing: mov eax, -1; finish: pop edi; pop edx; pop ecx; pop ebx; ret;'
    code = bytearray(assemble(source, address))
    marker = struct.pack('<I', 0x12345678)
    at = code.index(marker)
    # Four PUSH instructions, then CALL; anchor is address+9.
    code[at:at+4] = struct.pack('<i', names_iat - address - 9)
    return bytes(code)


def slider_stub(address, lookup, resume):
    # Only the non-enum ByteProperty slider branch uses this site.
    return assemble(f'''
        push eax; call {lookup}; cmp eax, -1; jne matched;
        mov eax, 255;
    matched: xchg eax, [esp];
        jmp {resume};
    ''', address)


def setter_stub(address, lookup, resume, reject):
    # Validate before ImportText: no byte overflow/wrap, no shared setter change.
    # Reject invalid input and use existing SendToControl/redraw path.
    return assemble(f'''
        mov [ebp - 0x10], esp;
        push eax; push ecx; push edx; push edi;
        call {lookup}; cmp eax, -1; je accepted;
        mov edx, eax; mov edi, [ebp + 8]; xor eax, eax;
        cmp word ptr [edi], 0; je denied;
    digit: movzx ecx, word ptr [edi]; test ecx, ecx; jz accepted;
        sub ecx, 48; cmp ecx, 9; ja denied;
        imul eax, eax, 10; add eax, ecx; cmp eax, edx; ja denied;
        add edi, 2; jmp digit;
    accepted: pop edi; pop edx; pop ecx; pop eax;
        mov ecx, [ebp + 8]; mov [ebp - 0x10], esp; jmp {resume};
    denied: pop edi; pop edx; pop ecx; pop eax; jmp {reject};
    ''', address)
