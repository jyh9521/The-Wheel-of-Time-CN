"""Execute native range adapters against synthetic property objects, not a game."""
import argparse
import json
import struct
from pathlib import Path
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *


def verify(dll, report=None):
    pe = pefile.PE(str(dll))
    checks = 0
    for base in (0x11000000, 0x21000000):
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
        uc.mem_write(base, pe.get_memory_mapped_image())
        uc.mem_map(0x30000000, 0x20000)
        item, prop, owner, package = 0x30001000, 0x30002000, 0x30003000, 0x30004000
        names, names_ref, text, frame, stack = 0x30005000, 0x30006000, 0x30007000, 0x30010000, 0x30018000
        def put(at, value): uc.mem_write(at, struct.pack('<I', value))
        def setup(name, owner_name='Client', package_name='Engine'):
            put(base+0x54734, names_ref); put(names_ref, names)
            put(item+0x3c, prop); put(prop+0x18, owner); put(prop+0x20, 0)
            put(owner+0x18, package); put(owner+0x20, 1); put(package+0x20, 2)
            for i, value in enumerate([name, owner_name, package_name]):
                ptr=0x30008000+i*0x1000
                put(names+i*4, ptr)
                uc.mem_write(ptr+12, (value+'\0').encode('utf-16le'))
            for reg, value in [(UC_X86_REG_ESI,item),(UC_X86_REG_EBP,frame),(UC_X86_REG_ESP,stack),
                               (UC_X86_REG_EAX,0x1234),(UC_X86_REG_EBX,0x2345),
                               (UC_X86_REG_ECX,0x3456),(UC_X86_REG_EDX,0x4567),(UC_X86_REG_EDI,0x5678)]:
                uc.reg_write(reg,value)
        # Original control: all non-enum byte properties expose 255.
        expected = {'MasterDetailLevel':2,'MaxDetailLevel':4,'GoreDetailLevel':3,
                    'ParticleDensity':255,'SoundVolume':255,'MusicVolume':255,'UnknownField':255}
        for name, maximum in expected.items():
            setup(name)
            uc.emu_start(base+0x19b58, base+0x19b5d, count=10000)
            actual=struct.unpack('<I',uc.mem_read(stack-4,4))[0]
            assert actual == (maximum if report else 255), (name,actual)
            assert uc.reg_read(UC_X86_REG_EAX)==0x1234
            assert uc.reg_read(UC_X86_REG_ECX)==0x3456
            assert uc.reg_read(UC_X86_REG_EDX)==0x4567
            checks += 1
        for limit in ([dict(property='MasterDetailLevel',maximum=2)] if not report else report['integer_limits']):
            name=limit['property']; maximum=limit['maximum']
            for value, allowed in [('0',True),(str(maximum),True),('0001',True),(str(maximum+1),False),
                                   ('255',maximum>=255),('999999999999999999999',False),('-1',False),
                                   ('',False),('1.5',False),('High',False)]:
                setup(name); put(frame+8,text); uc.mem_write(text,(value+'\0').encode('utf-16le'))
                reached=[]
                def stop(cpu, at, size, data):
                    if at in [base+0x18d06,base+0x18d1d]: reached.append(at);cpu.emu_stop()
                h=uc.hook_add(UC_HOOK_CODE,stop)
                uc.emu_start(base+0x18d00,base+0x18d20,count=10000);uc.hook_del(h)
                assert reached==[base+(0x18d06 if allowed or not report else 0x18d1d)],(name,value,reached)
                assert uc.reg_read(UC_X86_REG_ESP)==stack
                for reg, v in [(UC_X86_REG_EAX,0x1234),(UC_X86_REG_EBX,0x2345),(UC_X86_REG_EDX,0x4567),(UC_X86_REG_EDI,0x5678)]:
                    assert uc.reg_read(reg)==v
                assert bytes(uc.mem_read(text,len((value+'\0').encode('utf-16le'))))==(value+'\0').encode('utf-16le')
                checks+=1
        if report:
            for name,own,pkg in [('MasterDetailLevel','OtherClient','Engine'),('MasterDetailLevel','Client','OtherPackage'),
                                 ('SoundVolume','Client','Engine'),('ParticleDensity','Client','Engine'),('CacheSizeMegs','Client','Engine')]:
                setup(name,own,pkg);put(frame+8,text);uc.mem_write(text,('255\0').encode('utf-16le'))
                uc.emu_start(base+0x18d00,base+0x18d06,count=10000)
                assert uc.reg_read(UC_X86_REG_ESP)==stack
                checks+=1
    print(('MODIFIED' if report else 'BASELINE')+f' RANGE PASS: {checks} CPU checks; 2 image bases; '+
          ('per-property slider limits and invalid input rejection; unrelated fields unchanged' if report else
           'original MasterDetailLevel slider max=255 and setter accepts 255; invalid setting reproduced without game'))
    return checks


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dll',type=Path,required=True);p.add_argument('--report',type=Path)
    a=p.parse_args();verify(a.dll,json.loads(a.report.read_text()) if a.report else None)
