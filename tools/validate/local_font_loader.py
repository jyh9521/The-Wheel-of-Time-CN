"""Execute the emitted x86 font adapter with controlled Win32 API substitutes."""
import argparse,json,struct
from pathlib import Path
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from src.patch.local_font_loader import restore


def check(dll,manifest,base,path,faces=2,missing_api=False,gdi_absent=False):
    uc=Uc(UC_ARCH_X86,UC_MODE_32);image=pefile.PE(data=dll).get_memory_mapped_image()
    uc.mem_map(base,0x60000);uc.mem_write(base,image)
    uc.mem_map(0x20000000,0x10000);uc.mem_map(0x71000000,0x1000)
    funcs={'GetModuleHandleA':(0x71000000,4),'GetProcAddress':(0x71000100,8),
           'LoadLibraryA':(0x71000200,4),'GetModuleFileNameW':(0x71000300,12),
           'AddFontResourceExW':(0x71000400,12)}
    for name,(addr,pop) in funcs.items():uc.mem_write(addr,b'\xc2'+struct.pack('<H',pop))
    for name,rva in manifest['imports'].items():uc.mem_write(base+rva,struct.pack('<I',funcs[name][0]))
    calls=[]
    def string(addr,wide=False):
        raw=bytearray();unit=2 if wide else 1
        while True:
            b=bytes(uc.mem_read(addr,unit));addr+=unit
            if not any(b):break
            raw.extend(b)
        return raw.decode('utf-16-le' if wide else 'ascii')
    def api(machine,addr,size,data):
        if addr==base+manifest['wrapper_rva']:uc.emu_stop();return
        name=next((n for n,(a,_) in funcs.items() if a==addr),None)
        if not name:return
        sp=uc.reg_read(UC_X86_REG_ESP)
        def arg(n):return struct.unpack('<I',uc.mem_read(sp+4+n*4,4))[0]
        if name=='GetModuleHandleA':
            module=string(arg(0)).lower();ret=0x9000 if module=='kernel32.dll' else (0 if gdi_absent else 0xa000)
        elif name=='LoadLibraryA':assert string(arg(0)).lower()=='gdi32.dll';ret=0xa000
        elif name=='GetProcAddress':
            target=string(arg(1));ret=0 if missing_api and target=='GetModuleFileNameW' else funcs[target][0]
        elif name=='GetModuleFileNameW':
            assert arg(0)==base and arg(2)==900
            text=path[:899];uc.mem_write(arg(1),(text+'\0').encode('utf-16-le'));ret=len(text)
        else:
            expected=path[:max(path.rfind('\\'),path.rfind('/'))+1]+'..\\'+manifest['relative_font'].replace('/','\\')
            actual=string(arg(0),True);assert actual==expected,(actual,expected)
            assert arg(1)==0x10 and arg(2)==0;ret=faces
        calls.append(name);uc.reg_write(UC_X86_REG_EAX,ret)
        uc.reg_write(UC_X86_REG_ECX,0xdead0101);uc.reg_write(UC_X86_REG_EDX,0xdead0202)
    uc.hook_add(UC_HOOK_CODE,api)
    regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
    for reg,value in zip(regs,[11,22,33,44,55,66,77]):uc.reg_write(reg,value)
    uc.reg_write(UC_X86_REG_ESP,0x2000e000);uc.reg_write(UC_X86_REG_EFLAGS,0x246)
    uc.mem_write(0x2000e000,struct.pack('<II',0x70000000,0))
    before=[uc.reg_read(reg)for reg in regs]+[uc.reg_read(UC_X86_REG_ESP),uc.reg_read(UC_X86_REG_EFLAGS)]
    for n in range(2):
        uc.emu_start(base+manifest['loader_rva'],base+0x60000,count=10000)
        after=[uc.reg_read(reg)for reg in regs]+[uc.reg_read(UC_X86_REG_ESP),uc.reg_read(UC_X86_REG_EFLAGS)]
        assert before==after,(before,after)
    expected_add=0 if missing_api or len(path)>=899 or ('\\' not in path and '/' not in path) else (1 if faces else 2)
    assert calls.count('AddFontResourceExW')==expected_add,calls
    assert struct.unpack('<I',uc.mem_read(base+manifest['state_rva'],4))[0]==(faces if expected_add else 0)
    return len(calls)


def run(dll,manifest):
    restore(dll,manifest)
    count=0
    cases=[dict(path='C:\\Games\\WoT\\System\\WinDrv.dll'),
           dict(path='F:\\字幕测试\\System\\WinDrv.dll'),
           dict(path='C:/Games/WoT/System/WinDrv.dll'),
           dict(path='C:\\Games\\WoT\\System\\WinDrv.dll',faces=0),
           dict(path='C:\\Games\\WoT\\System\\WinDrv.dll',missing_api=True),
           dict(path='C:\\Games\\WoT\\System\\WinDrv.dll',gdi_absent=True),
           dict(path='C:\\'+'a'*920),dict(path='WinDrv.dll')]
    for base in [0x11100000,0x13000000]:
        for case in cases:count+=check(dll,manifest,base,**case)
    print('LOADER CPU PASS: 16 scenarios; %d API calls; relocated/Unicode paths; success cache; missing font/API; registers/flags/stack preserved' % count)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dll',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();run(a.dll.read_bytes(),json.loads(a.manifest.read_text('utf8')))
