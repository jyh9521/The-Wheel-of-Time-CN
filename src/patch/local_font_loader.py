"""Hash-gated x86 PlayMovie pre-initialization private-font adapter (isolated PoC)."""
import json
import struct
from pathlib import PurePosixPath
import pefile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
from src.patch.movie_player import patch as select_text, sha


def assemble(rva, state_rva, wrapper, imports, strings):
    asm = f'''
        pushfd
        pushad
        call get_pc
    get_pc:
        pop ebx
        sub ebx, {rva+7}
        sub esp, 0x800
        cmp dword ptr [ebx+{state_rva}], 0
        jne done
        lea eax, [ebx+{strings['kernel']}]
        push eax
        call dword ptr [ebx+{imports['GetModuleHandleA']}]
        test eax, eax
        jz done
        lea edx, [ebx+{strings['filename_api']}]
        push edx
        push eax
        call dword ptr [ebx+{imports['GetProcAddress']}]
        test eax, eax
        jz done
        mov ebp, eax
        mov esi, esp
        push 900
        push esi
        push ebx
        call ebp
        test eax, eax
        jz done
        cmp eax, 899
        jae done
        lea edi, [esi+eax*2]
    find_slash:
        cmp edi, esi
        jbe done
        sub edi, 2
        cmp word ptr [edi], 0x5c
        je found
        cmp word ptr [edi], 0x2f
        jne find_slash
    found:
        add edi, 2
        lea esi, [ebx+{strings['suffix']}]
        mov ecx, {strings['suffix_chars']}
        cld
        rep movsw
        lea eax, [ebx+{strings['gdi']}]
        push eax
        call dword ptr [ebx+{imports['GetModuleHandleA']}]
        test eax, eax
        jnz have_gdi
        lea eax, [ebx+{strings['gdi']}]
        push eax
        call dword ptr [ebx+{imports['LoadLibraryA']}]
        test eax, eax
        jz done
    have_gdi:
        lea edx, [ebx+{strings['font_api']}]
        push edx
        push eax
        call dword ptr [ebx+{imports['GetProcAddress']}]
        test eax, eax
        jz done
        mov ebp, eax
        mov esi, esp
        push 0
        push 0x10
        push esi
        call ebp
        mov dword ptr [ebx+{state_rva}], eax
    done:
        add esp, 0x800
        popad
        popfd
        jmp {wrapper}
    '''
    encoded, _ = Ks(KS_ARCH_X86, KS_MODE_32).asm(asm, addr=rva)
    return bytes(encoded), asm


def patch(original, selector_profile, relative_font):
    rel=PurePosixPath(relative_font)
    if rel.is_absolute() or '..' in rel.parts or not relative_font.isascii() or ':' in relative_font or not relative_font.endswith('.ttf'):
        raise ValueError('Font must have a relative ASCII TTF path inside the game')
    data, selector=select_text(original,selector_profile)
    pe=pefile.PE(data=data)
    if pe.FILE_HEADER.Machine!=0x14c or len(pe.sections)!=6 or pe.OPTIONAL_HEADER.SizeOfImage!=0x50000:
        raise ValueError('Unknown PE layout')
    if pe.get_offset_from_rva(0xf982)!=0xf982 or data[0xf982:0xf987].hex()!='e8c9840000':
        raise ValueError('Unexpected InitializeQTML call')
    if pe.OPTIONAL_HEADER.FileAlignment!=0x1000 or len(data)!=0x50000:
        raise ValueError('Unknown section/file alignment')
    slot=pe.sections[-1].get_file_offset()+40
    if slot+80>pe.OPTIONAL_HEADER.SizeOfHeaders or any(data[slot:slot+80]):
        raise ValueError('No clean section-header slots')
    imports={i.name.decode():i.address-pe.OPTIONAL_HEADER.ImageBase
             for desc in pe.DIRECTORY_ENTRY_IMPORT if desc.dll.lower()==b'kernel32.dll' for i in desc.imports}
    imports={name:imports[name] for name in ['GetModuleHandleA','GetProcAddress','LoadLibraryA']}
    code_rva=0x50000;state_rva=0x51000;constants=bytearray();strings={}
    values={'kernel':b'kernel32.dll\0','filename_api':b'GetModuleFileNameW\0',
            'gdi':b'gdi32.dll\0','font_api':b'AddFontResourceExW\0',
            'suffix':('..\\'+relative_font.replace('/','\\')+'\0').encode('utf-16-le')}
    for name,value in values.items():
        if name=='suffix' and len(constants)%2:constants.append(0)
        strings[name]=code_rva+0x400+len(constants);constants.extend(value)
    strings['suffix_chars']=len(values['suffix'])//2
    code,assembly=assemble(code_rva,state_rva,0x17e50,imports,strings)
    if len(code)>0x400 or len(constants)>0x400:raise ValueError('Adapter section overflow')
    result=bytearray(data);result.extend(bytes(0x2000));edits=[]
    def edit(offset,after):
        before=bytes(result[offset:offset+len(after)])
        result[offset:offset+len(after)]=after
        edits.append(dict(offset=offset,before=before.hex(),after=after.hex()))
    # Both section headers and aggregate PE sizes are synchronized.
    edit(pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),struct.pack('<H',8))
    for name,increment in [('SizeOfCode',0x1000),('SizeOfInitializedData',0x1000),('SizeOfImage',0x2000)]:
        edit(pe.OPTIONAL_HEADER.get_field_absolute_offset(name),struct.pack('<I',getattr(pe.OPTIONAL_HEADER,name)+increment))
    edit(slot,struct.pack('<8sIIIIIIHHI',b'.lfcode',0x800,code_rva,0x1000,code_rva,0,0,0,0,0x60000020))
    edit(slot+40,struct.pack('<8sIIIIIIHHI',b'.lfdata',4,state_rva,0x1000,state_rva,0,0,0,0,0xc0000040))
    edit(0xf982,b'\xe8'+struct.pack('<i',code_rva-(0xf982+5)))
    result[code_rva:code_rva+len(code)]=code
    result[code_rva+0x400:code_rva+0x400+len(constants)]=constants
    result=bytes(result)
    manifest=dict(source_sha256=sha(original),source_size=len(original),output_sha256=sha(result),
                  output_size=len(result),selector=selector,edits=edits,
                  relative_font=relative_font,loader_rva=code_rva,state_rva=state_rva,
                  wrapper_rva=0x17e50,imports=imports,strings=strings,assembly=assembly,
                  field='PlayMovie InitializeQTML pre-call; FR_PRIVATE font registration; first text track',
                  register_and_flag_preservation=True,position_independent=True,
                  audio_path_unchanged=True,loader_lock=False)
    check=pefile.PE(data=result)
    assert len(check.sections)==8 and check.OPTIONAL_HEADER.SizeOfImage==0x52000
    assert restore(result,manifest)==original
    return result,manifest


def restore(data,manifest):
    if len(data)!=manifest['output_size'] or sha(data)!=manifest['output_sha256']:
        raise ValueError('Modified DLL identity mismatch')
    result=bytearray(data[:manifest['source_size']])
    for edit in reversed(manifest['edits']):
        offset=edit['offset'];before=bytes.fromhex(edit['before']);after=bytes.fromhex(edit['after'])
        if result[offset:offset+len(after)]!=after:raise ValueError('Adapter rollback mismatch')
        result[offset:offset+len(before)]=before
    from src.patch.movie_player import restore as restore_selector
    result=restore_selector(bytes(result),manifest['selector'])
    if sha(result)!=manifest['source_sha256']:raise ValueError('Original DLL was not restored')
    return result
