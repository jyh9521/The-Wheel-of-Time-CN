"""Read every active-copy file; audit readable text paths without launching the game.
Binary literal candidates and empty sounds are not automatically display text.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
from tools.pack.ue1 import Package,body,Reader
from tools.extract.int_files import entries as int_entries
from tools.extract.map_messages import entries as map_entries
from tools.pack.movie_text import text_tables,read_translations,wrap
ROOT=Path(__file__).resolve().parents[2]
LATIN=re.compile(r'[A-Za-z]{3,}')

def fingerprint(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(2*1024*1024):h.update(chunk)
    return h.hexdigest()

def catalog_readback(game, rows):
    """Verify final files, rather than assuming a successful import survived later stages."""
    tables={};failures=[]
    for row in rows:
        if not row.get('translation'):continue
        file=row['file']
        if file not in tables:
            path=game/'System'/file
            tables[file]={(r['section'],r['key'],r['occurrence']):r['source'] for r in int_entries(path)} if path.is_file() else {}
        key=(row['section'],row['key'],row['occurrence']);actual=tables[file].get(key)
        if actual is None or actual.rstrip()!=row['translation'].rstrip():
            failures.append(dict(file=file,section=row['section'],key=row['key'],occurrence=row['occurrence'],expected=row['translation'],actual=actual))
    return failures

def class_defaults(game):
    """Research candidates, not proof of effective runtime localization.

    A localized UClass default may legitimately remain English in the package:
    the corresponding INT entry overrides it when the class loads. Missing
    exact entries can also inherit a localized superclass value.
    """
    from tools.extract.class_defaults import discover
    packs={p.stem.casefold():Package(p) for p in (game/'System').glob('*.u')}
    records={n:p.records() for n,p in packs.items()}
    classes={n:{r['path']:r for r in records[n] if p.exports[r['index']-1]['cls']==0} for n,p in packs.items()}
    own={};cache={}
    for n,p in packs.items():
        for r in records[n]:
            if r['class_name'].endswith('Property') and '.' in r['path']:
                owner,key=r['path'].rsplit('.',1);rd=Reader(body(p,r['index']))
                rd.idx();rd.idx();rd.idx();rd.i32();flags=rd.i32()
                own.setdefault((n,owner),{})[key]=flags
    def members(n,c,trail=()):
        if (n,c) in cache:return cache[n,c]
        if (n,c) in trail:return {}
        p=packs[n];r=classes[n][c];idx=p.exports[r['index']-1]['super'];s=p.full(idx);parent={}
        if idx>0 and s in classes[n]:parent=members(n,s,trail+((n,c),))
        elif idx<0:
            parts=s.split('.');pn=parts[0].casefold();pc='.'.join(parts[1:])
            if pn in classes and pc in classes[pn]:parent=members(pn,pc,trail+((n,c),))
        result=parent|own.get((n,c),{});cache[n,c]=result;return result
    tables={p.stem.casefold():{(r['section'].casefold(),r['key'].casefold()):r['source'] for r in int_entries(p)} for p in (game/'System').glob('*.int')}
    defaults=[]
    for n,p in packs.items():
        for cls,r in classes[n].items():
            props=members(n,cls);offset,tags=discover(p,r,set(props))
            for t in tags:
                if t['type']!=13 or not t.get('source','').strip():continue
                table=tables.get(n,{})
                # Scalar/array identity is not guessed when slot zero is used.
                key=t['property'].casefold();keys=[key,key+'['+str(t['slot'])+']']
                exact=next((table[cls.casefold(),k] for k in keys if (cls.casefold(),k)in table),None)
                defaults.append(dict(file='System/'+p.path.name,cls=cls,property=t['property'],slot=t['slot'],text=t['source'],localized=bool(props[t['property']]&0x8000),defaults_offset=offset,exact_int=exact))
    return defaults

def run(game,locale,out):
    game,out=game.resolve(),out.resolve()
    if out.is_relative_to(game):raise ValueError('Audit output must be outside the game')
    out.mkdir(parents=True,exist_ok=True)
    inventory=[];ints=[];maps=[];literals=[];movies=[];errors=[];sounds=[]
    lex=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|[()]',re.S)
    display={'drawtext','drawtextclipped','addhandmessage','addleftmessage','addrightmessage','addcentermessage','addsubtitlemessage','addgenericmessage','clientmessage','broadcastmessage','settext','message','sethelptext','additem','addchoice'}
    fmv_profile=json.loads((ROOT/'profiles/fmv-movies.json').read_text('utf8'))
    fmvs={m['movie']:m for m in fmv_profile['movies']}
    fmv_config=json.loads((ROOT/'locales'/locale/'fmv/local-font-poc.json').read_text('utf8'))
    for path in sorted(game.rglob('*')):
        if not path.is_file():continue
        name=path.relative_to(game).as_posix();suffix=path.suffix.lower()
        item=dict(file=name,size=path.stat().st_size,sha256=fingerprint(path),method='binary fingerprint',status='not a parsed text carrier')
        inventory.append(item)
        try:
            if path.parts[-2]=='System' and suffix=='.int':
                rows=int_entries(path);item.update(method='INI sections/keys/values',entries=len(rows),status='parsed')
                ints.extend(dict(r,file=name) for r in rows if LATIN.search(r['source']))
            elif path.parts[-2]=='Maps' and suffix in ('.wot','.unr'):
                rows=map_entries(path,False,True);item.update(method='actor FString property streams',entries=len(rows),status='parsed')
                maps.extend(dict(r,file=name) for r in rows if r['active'])
            elif suffix in ('.u','.utx','.uax','.umx') and path.parts[-2]in ('System','Textures','Sounds','Music'):
                p=Package(path);records=p.records();counts=dict(collections.Counter(r['class_name']for r in records))
                item.update(method='UE package identity/export tables',exports=len(records),classes=counts,status='parsed')
                sounds.extend(dict(file=name,sound=path.stem+'.'+r['path']) for r in records if r['class_name']=='Sound')
                code=b'\n'.join(body(p,r['index'])for r in records if r['class_name']in ('Function','State'))
                raw_candidates=[]
                for r in records:
                    if r['class_name']in ('Function','State'):
                        raw=body(p,r['index'])
                        raw_candidates.extend(dict(export=r['path'],offset=m.start(),text=m[1].decode('ascii'))for m in re.finditer(rb'\x1f([\x20-\x7e]{3,})\x00',raw)if LATIN.search(m[1].decode('ascii')))
                    if r['class_name']!='TextBuffer':continue
                    raw=body(p,r['index']);rd=Reader(raw)
                    if p.names[rd.idx()]!='None':raise ValueError('TextBuffer has unexpected properties')
                    rd.p+=8;s=rd.string(p.ver)
                    if rd.p!=len(raw):raise ValueError('Unknown TextBuffer layout')
                    stack=[];last=''
                    for m in lex.finditer(s):
                        t=m[0]
                        if t.startswith('//')or t.startswith('/*'):continue
                        if t=='(':stack.append(last.lower())
                        elif t==')':
                            if stack:stack.pop()
                        elif t.startswith('"'):
                            text=t[1:-1]
                            if any(c in display for c in stack)and LATIN.search(text)and b'\x1f'+text.encode('cp1252',errors='replace')+b'\0'in code:
                                literals.append(dict(file=name,source=r['path'],line=s.count('\n',0,m.start())+1,text=text,call=stack[-1]if stack else'',context=s[max(0,m.start()-140):m.end()+140]))
                        last=t
                item['literal_candidates']=len(raw_candidates)
                if raw_candidates:(out/(path.name+'.literal-candidates.json')).write_text(json.dumps(raw_candidates,ensure_ascii=False,indent=2),'utf8')
            elif path.parts[-2]=='Movies'and suffix=='.mov':
                spec=fmvs.get(path.name)
                if spec is None:raise ValueError('Movie missing from version inventory')
                table=text_tables(path.read_bytes(),spec['track_id']) if spec['track_id']is not None else None
                if table:
                    rows=read_translations(ROOT/'locales'/locale/'fmv'/(path.stem+'.tsv'))
                    expected={k:wrap(v,fmv_config['line_units'])for k,v in rows.items()}
                    actual={r['index']:r['text']for r in table['samples']if r['nonempty']}
                    movies.append(dict(file=name,track_id=table['track_id'],nonempty=len(actual),matches_translation=actual==expected,latin=[k for k,v in actual.items()if LATIN.search(v)]))
                    item.update(method='selected QuickTime text samples and timings',entries=len(actual),status='parsed')
                else:
                    movies.append(dict(file=name,track_id=None,status='no selected subtitle track; speech coverage requires separate evidence'))
                    item.update(method='movie inventory: no selected text track',status='non-text media')
            elif suffix in ('.ini','.txt','.cfg','.md','.json','.tsv','.html','.htm'):
                raw=path.read_bytes()
                item.update(method='complete text bytes; settings/commands/docs kept distinct',status='read',has_latin=bool(re.search(rb'[A-Za-z]{3,}',raw)))
            elif suffix in ('.exe','.dll','.ocx'):
                raw=path.read_bytes()
                ascii_strings=[m[0].decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{5,}',raw) if LATIN.search(m[0].decode('ascii'))]
                wide_strings=[m[0].decode('utf-16le') for m in re.finditer(rb'(?:[\x20-\x7e]\x00){5,}',raw) if LATIN.search(m[0].decode('utf-16le'))]
                item.update(method='complete PE bytes; ASCII/UTF16 candidate strings',status='display reachability unresolved',ascii_candidates=len(ascii_strings),utf16_candidates=len(wide_strings))
                (out/(path.name+'.native-candidates.json')).write_text(json.dumps(dict(ascii=ascii_strings,utf16=wide_strings),ensure_ascii=False,indent=2),'utf8')
        except (ValueError,AssertionError,IndexError,KeyError,UnicodeError)as e:
            errors.append(dict(file=name,error=str(e)));item['status']='unparsed: '+str(e)
    subtitles={(r['section'].casefold(),r['key'].casefold()):r for r in int_entries(game/'System/WoTsubtitles.int')}
    sound_state=[]
    for r in sounds:
        parts=r['sound'].split('.');key=(parts[-2].casefold(),parts[-1].casefold());sub=subtitles.get(key)
        sound_state.append(dict(r,state='missing-key'if sub is None else 'empty'if sub['empty']else'text'))
    defaults=class_defaults(game)
    rows=json.loads((ROOT/'locales'/locale/'strings.json').read_text('utf8'))
    config=json.loads((ROOT/'locales'/locale/'config.json').read_text('utf8'))
    if config.get('subtitle_rows'):
        from tools.build.source_layer import compose_rows,load_rows
        manifest=json.loads((ROOT/'profiles/subtitle-source.json').read_text('utf8'))
        rows=compose_rows(rows,load_rows(ROOT/'locales'/locale,config,manifest),load_rows(ROOT/'locales'/locale,config,manifest,'subtitle_overrides'),manifest)
    if config.get('native_ui'):
        rows+=json.loads((ROOT/'locales'/locale/config['native_ui']).read_text('utf8'))['strings']
    readback=catalog_readback(game,rows)
    changed=[r['file']for r in inventory if fingerprint(game/r['file'])!=r['sha256']]
    report=dict(game=str(game),locale=locale,files=inventory,errors=errors,input_changes=changed,
        int_latin_candidates=ints,map_strings=maps,compiled_display_candidates=literals,class_default_candidates=defaults,catalog_readback_failures=readback,movies=movies,sounds=sound_state,
        conclusion='inventory/readback is not proof of every runtime branch, audible line, native string or image text',
        runtime_verified=False,all_text_chinese_verified=False)
    (out/'AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(f"AUDIT READ PASS: {len(inventory)} files fully hashed/read; {len(errors)} parser gaps; {len(changed)} input changes; {len(ints)} INT Latin candidates; {len(literals)} source/code-linked display candidates; {len(defaults)} class default strings")
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--locale',default='zh-CN');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--require-complete',action='store_true',help='Fail unless complete runtime coverage has been demonstrated')
    a=p.parse_args();result=run(a.game_dir,a.locale,a.out)
    if result['errors'] or result['input_changes'] or result['catalog_readback_failures'] or any(m.get('matches_translation') is False for m in result['movies']):
        raise SystemExit(1)
    if a.require_complete and not result['all_text_chinese_verified']:
        print('COVERAGE INCOMPLETE: runtime/native/audio/display candidates remain unresolved')
        raise SystemExit(2)
