"""Read-only enumeration of preference declarations and available property evidence."""
import argparse
import hashlib
import importlib
import json
import re
import struct
from pathlib import Path
from tools.pack.ue1 import Package, body


def audit(game, output, profile, labels):
    import pefile
    import capstone
    fields=importlib.import_module('tools.import.preferences').fields
    config=json.loads(labels.read_text('utf8'))
    native=json.loads(profile.read_text('utf8'))['native_properties']
    names=set(config['labels'])
    preferences=[];records=[];hashes={};refs={name:[]for name in names}
    def sha(data):return hashlib.sha256(data).hexdigest()
    for path in sorted((game/'System').glob('*.int')):
        for number,line in enumerate(path.read_bytes().decode('cp1252').splitlines(),1):
            if line.startswith('Preferences='):
                preferences.append(dict(file=path.name,line=number,**fields(line.split('=',1)[1])))
    for path in sorted((game/'System').glob('*.u')):
        pkg=Package(path);hashes[path.name]=sha(pkg.b)
        for item in pkg.records():
            if item['class_name'].endswith('Property') and item['path'].rsplit('.',1)[-1] in names:
                records.append(dict(file=path.name,path=item['path'],kind=item['class_name'],offset=item['offset']))
            if item['class_name']=='TextBuffer':
                text=body(pkg,item['index']).decode('cp1252',errors='replace')
                for name in names:
                    if re.search(r'\b'+re.escape(name)+r'\b',text):
                        refs[name].append(dict(file=path.name,export=item['path'],sha256=sha(body(pkg,item['index']))))
    decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    for path in sorted((game/'System').glob('*.dll')):
        pe=pefile.PE(str(path));hashes[path.name]=sha(path.read_bytes())
        if not hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):continue
        base=pe.OPTIONAL_HEADER.ImageBase
        imports={i.address:i.name.decode('ascii') for e in pe.DIRECTORY_ENTRY_IMPORT for i in e.imports if i.name} if hasattr(pe,'DIRECTORY_ENTRY_IMPORT') else {}
        def vtable_kind(address):
            if not base<=address<base+pe.OPTIONAL_HEADER.SizeOfImage:return None
            try:values=struct.unpack('<57I',pe.get_data(address-base,228))
            except (pefile.PEFormatError,struct.error):return None
            for value in values:
                if not base<=value<base+pe.OPTIONAL_HEADER.SizeOfImage:continue
                code=pe.get_data(value-base,6)
                if code[:2]!=b'\xff\x25':continue
                symbol=imports.get(struct.unpack('<I',code[2:])[0],'')
                match=re.match(r'\?Serialize@U(\w+Property)@@',symbol)
                if match:return match[1]
            return None
        for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if not symbol.name or not symbol.name.startswith(b'?StaticConstructor@'):continue
            name=symbol.name.decode('ascii');owner=name.split('@')[1].removeprefix('U')
            first=next(decoder.disasm(pe.get_data(symbol.address,5),base+symbol.address),None)
            if first is None:continue
            start=int(first.op_str,16)-base if first.mnemonic=='jmp' else symbol.address
            # Constructors contain one straight-line registration sequence ending in RET.
            instructions=list(decoder.disasm(pe.get_data(start,24000),base+start))
            for j,ins in enumerate(instructions):
                if ins.mnemonic=='ret':break
                if ins.mnemonic!='push' or not ins.op_str.startswith('0x'):continue
                addr=int(ins.op_str,16)-base
                if not 0<=addr<pe.OPTIONAL_HEADER.SizeOfImage:continue
                raw=pe.get_data(addr,120)
                try:value=raw[:len(raw)//2*2].decode('utf-16le').split('\0',1)[0]
                except UnicodeError:continue
                if value in names:
                    following=instructions[j+1] if j+1<len(instructions) else None
                    if following is None or following.mnemonic!='call' or not following.op_str.startswith('dword ptr [0x'):
                        continue
                    imported=imports.get(int(following.op_str[11:-1],16),'')
                    if not imported.startswith('??0FName@@'):
                        continue
                    kind='native-registration'
                    byte_mapping=None
                    for after in instructions[j+1:j+30]:
                        if after.mnemonic=='mov' and after.op_str.startswith('dword ptr [esi], 0x'):
                            kind=vtable_kind(int(after.op_str.split(', ')[1],16)) or kind
                            break
                    if kind=='ByteProperty':
                        for after in instructions[j+1:j+30]:
                            if after.mnemonic=='mov' and after.op_str.startswith('dword ptr [esi + 0x5c], '):
                                byte_mapping='raw-byte' if after.op_str.endswith(', 0') else 'enum-backed'
                                break
                    records.append(dict(file=path.name,path=owner+'.'+value,kind=kind,
                                        constructor=name,rva=ins.address-base,byte_mapping=byte_mapping))
    limits={x['property']:x for x in native['integer_limits']}
    inventory=[]
    for name in sorted(names):
        declarations=[r for r in records if r['path'].rsplit('.',1)[-1]==name]
        if name in limits:
            status='profiled editor limit from original menu contract';limit=limits[name]
        elif name in {'SoundVolume','MusicVolume','ParticleDensity'}:
            status='preserve original 0..255 range';limit=dict(minimum=0,maximum=255)
        else:
            status='no new numeric bound: label/category or unverified consumer limit';limit=None
        inventory.append(dict(name=name,declarations=declarations,script_references=refs[name],limit=limit,status=status))
    output.parent.mkdir(parents=True,exist_ok=True)
    result=dict(preferences=preferences,inventory=inventory,input_sha256=hashes,
                note='Enumeration is not a proof that every numeric value is valid. Unknown bounds remain unchanged; no guessed global clamp.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'ADVANCED AUDIT PASS: {len(preferences)} preference declarations; {len(inventory)} display identifiers; {len(records)} property declarations; {len(hashes)} hashed package/DLL inputs; unknown ranges explicitly marked')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--profile',type=Path,default=Path('profiles/gog-v68.json'));p.add_argument('--labels',type=Path,default=Path('locales/zh-CN/native-properties.json'))
    a=p.parse_args();audit(a.game_dir,a.out,a.profile,a.labels)
