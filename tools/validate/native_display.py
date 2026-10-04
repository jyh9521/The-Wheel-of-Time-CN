"""Execute copied display stubs in x86 emulation, not in the game process."""
import argparse
import json
import struct
from pathlib import Path
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                              UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI,
                              UC_X86_REG_EBP, UC_X86_REG_ESP)


def text_at(uc, pointer):
    data = bytearray()
    for i in range(1024):
        unit = bytes(uc.mem_read(pointer + i * 2, 2))
        if unit == b'\0\0':
            return bytes(data).decode('utf-16le')
        data += unit
    raise ValueError('Unterminated native display string')


def verify(path, data, report, spec):
    pe = pefile.PE(str(path))
    assertions = 0
    for base in (0x11000000, 0x21000000):
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        size = (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095
        uc.mem_map(base, size)
        uc.mem_write(base, pe.get_memory_mapped_image())
        uc.mem_map(0x30000000, 0x10000)
        stack, source, frame, end = 0x3000e000, 0x30001000, 0x30008000, 0x3000f000
        preserved = {UC_X86_REG_EBX:0x1234, UC_X86_REG_ECX:0x2345,
                     UC_X86_REG_EDX:0x3456, UC_X86_REG_ESI:0x4567, UC_X86_REG_EDI:0x5678}

        def reset():
            for reg, value in preserved.items():
                uc.reg_write(reg, value)
            uc.reg_write(UC_X86_REG_EBP, frame)
            uc.reg_write(UC_X86_REG_ESP, stack)
            uc.mem_write(stack, struct.pack('<I', end))

        for kind in ('labels', 'values'):
            pairs = dict(data[kind], **{'unknown_value_123':'unknown_value_123', '':''})
            rva = report['label_lookup_rva' if kind == 'labels' else 'value_lookup_rva']
            for original, translated in pairs.items():
                reset()
                uc.mem_write(source, (original + '\0').encode('utf-16le'))
                uc.reg_write(UC_X86_REG_EAX, source)
                uc.emu_start(base + rva, end, count=100000)
                assert text_at(uc, uc.reg_read(UC_X86_REG_EAX)) == translated
                assert uc.reg_read(UC_X86_REG_ESP) == stack + 4
                assert all(uc.reg_read(reg) == value for reg, value in preserved.items())
                assert text_at(uc, source) == original
                assertions += 1
        for name, at, expected in spec['caption_sites']:
            reset()
            uc.mem_write(source, b'\0' * 12 + ('TextureDetail\0').encode('utf-16le'))
            uc.reg_write(UC_X86_REG_EAX, source)
            uc.emu_start(base + at, base + at + len(bytes.fromhex(expected)), count=100000)
            pointer = uc.reg_read(UC_X86_REG_EAX)
            assert text_at(uc, pointer) == data['labels']['TextureDetail']
            if name == 'property_draw':
                assert uc.reg_read(UC_X86_REG_ESP) == stack - 8
                assert struct.unpack('<II', uc.mem_read(stack - 8, 8)) == (preserved[UC_X86_REG_ECX], pointer)
            else:
                assert struct.unpack('<I', uc.mem_read(frame - 0x18, 4))[0] == pointer
                assert uc.reg_read(UC_X86_REG_ESP) == stack
            assert all(uc.reg_read(reg) == value for reg, value in preserved.items())
            assertions += 1
        for original, translated in dict(data['values'], CustomServer='CustomServer').items():
            reset()
            uc.mem_write(frame - 0x20b4, (original + '\0').encode('utf-16le'))
            uc.mem_write(source, struct.pack('<I', 0x123456))
            uc.reg_write(UC_X86_REG_ESI, source)
            uc.emu_start(base + spec['value_draw_rva'], base + spec['value_draw_rva'] + 5, count=100000)
            assert text_at(uc, frame - 0x20b4) == translated
            assert uc.reg_read(UC_X86_REG_ECX) == source
            assert uc.reg_read(UC_X86_REG_EDX) == 0x123456
            assert uc.reg_read(UC_X86_REG_ESI) == source
            assert uc.reg_read(UC_X86_REG_ESP) == stack - 4
            assertions += 1
        # Execute every copied combo adapter through a simulated original
        # thiscall method. Verify UTF-16 arguments, cleanup and raw write-back.
        for site in report.get('editor_sites', []):
            samples = dict(data['values'], CustomServer='CustomServer')
            for raw, display in samples.items():
                reset()
                table, callee = 0x30002000, 0x3000f100
                observed = []
                kind = site['kind']
                inp = display if kind == 'combo_save' else raw
                uc.mem_write(source, (inp + '\0').encode('utf-16le'))
                uc.mem_write(callee, b'\xc2\x04\x00')
                slot = 0x80 if kind == 'combo_save' else (0xb8 if kind == 'combo_add' else 0xcc)
                uc.mem_write(table + slot, struct.pack('<I', callee))
                uc.reg_write(UC_X86_REG_EDX, table)
                uc.reg_write(UC_X86_REG_ESI, 0x4567)
                uc.reg_write(UC_X86_REG_EAX, source)
                if kind != 'combo_save':
                    uc.mem_write(stack, struct.pack('<I', source))
                def capture(cpu, address, size, unused):
                    if address == callee:
                        arg = struct.unpack('<I', cpu.mem_read(cpu.reg_read(UC_X86_REG_ESP) + 4, 4))[0]
                        observed.append((text_at(cpu, arg), cpu.reg_read(UC_X86_REG_ECX)))
                hook = uc.hook_add(UC_HOOK_CODE, capture)
                uc.emu_start(base + site['rva'], base + site['rva'] + len(bytes.fromhex(site['expected_hex'])), count=100000)
                uc.hook_del(hook)
                assert observed == [(raw if kind == 'combo_save' else display,
                                     0x4567 if kind == 'combo_save' else preserved[UC_X86_REG_ECX])]
                assert text_at(uc, source) == inp
                assert uc.reg_read(UC_X86_REG_ESP) == stack + (0 if kind == 'combo_save' else 4)
                assert uc.reg_read(UC_X86_REG_EDX) == table
                assert uc.reg_read(UC_X86_REG_ESI) == 0x4567
                assertions += 1
        for width in (128, 320, 500):
            reset()
            uc.mem_write(source + 0xc4, struct.pack('<i', width))
            uc.reg_write(UC_X86_REG_ECX, source)
            uc.emu_start(base + spec['divider_rva'], end, count=10000)
            assert uc.reg_read(UC_X86_REG_EAX) == max(width, data['minimum_divider_width'])
            assertions += 1
        for rva in spec['height_rvas']:
            reset()
            uc.emu_start(base + rva, end, count=10000)
            assert uc.reg_read(UC_X86_REG_EAX) == data['row_height']
            assertions += 1
    print(f'NATIVE EMULATION PASS: {assertions} checks; 2 image bases; UTF-16 lookup/fallback; registers/stack; caption/value paths; row height/divider; no game launched')
    return assertions


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dll', type=Path, required=True)
    p.add_argument('--data', type=Path, default=Path('locales/zh-CN/native-properties.json'))
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--profile', type=Path, default=Path('profiles/gog-v68.json'))
    a = p.parse_args()
    verify(a.dll, json.loads(a.data.read_text('utf8')), json.loads(a.report.read_text('utf8')),
           json.loads(a.profile.read_text('utf8'))['native_properties'])
