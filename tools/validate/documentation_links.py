"""Check repository Markdown links; optionally probe external HTTP destinations."""
from pathlib import Path
from urllib.parse import unquote, urlsplit, quote
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
import argparse, json, re, unicodedata

ROOT = Path(__file__).resolve().parents[2]

def documents(root=ROOT):
    return sorted(p for p in root.rglob('*.md') if not any(part in {'.git','build','dist','out','.venv','node_modules'} for part in p.relative_to(root).parts))

def links(text):
    text = re.sub(r'```.*?```|~~~.*?~~~', '', text, flags=re.S)
    # Balanced destinations support literal parentheses in wiki page names.
    for match in re.finditer(r'!?\[[^\]\n]*\]\(', text):
        start=match.end(); depth=1; end=start
        while end < len(text) and depth:
            if text[end]=='(' and (end==0 or text[end-1]!='\\'): depth+=1
            if text[end]==')' and (end==0 or text[end-1]!='\\'): depth-=1
            end+=1
        if not depth:
            target=text[start:end-1].strip()
            if target.startswith('<'): target=target[1:target.index('>')]
            else: target=re.split(r'\s+[\"\']',target,maxsplit=1)[0]
            yield target
    for match in re.finditer(r'^\s*\[[^\]]+\]:\s*<?([^\s>]+)',text,re.M): yield match[1]
    for match in re.finditer(r'<(https?://[^<>\s]+)>',text): yield match[1]

def anchors(text):
    result=set(); seen={}
    for match in re.finditer(r'^#{1,6}\s+(.+?)\s*#*$',text,re.M):
        title=re.sub(r'[`*_~]','',match[1]).lower()
        slug=''.join(c for c in title if c=='-' or c==' ' or unicodedata.category(c)[0] in {'L','N'}).replace(' ','-')
        number=seen.get(slug,0); seen[slug]=number+1
        result.add(slug if not number else f'{slug}-{number}')
    return result

def probe(url):
    parts=urlsplit(url); encoded=parts._replace(path=quote(unquote(parts.path),safe='/:%@+~()'),query=quote(unquote(parts.query),safe='=&%:+/?'),fragment='').geturl()
    try:
        with urlopen(Request(encoded,headers={'User-Agent':'Mozilla/5.0 (documentation-link-audit)'}),timeout=20) as response:
            return dict(url=url,status=response.status,final_url=response.url)
    except Exception as error:
        return dict(url=url,status=getattr(error,'code',None),error=str(error))

def audit(root=ROOT, external=False):
    local=[]; urls=set(); count=0; fs=documents(root)
    for path in fs:
        for target in links(path.read_text('utf8')):
            count+=1
            if target.startswith(('https://','http://')): urls.add(target); continue
            if target.startswith(('mailto:','data:')): continue
            base,_,fragment=target.partition('#'); dest=path if not base else path.parent/unquote(base)
            reason=None
            if re.match(r'^[A-Za-z]:',base) or base.startswith('\\'): reason='machine-local path'
            elif not dest.exists(): reason='missing target'
            elif fragment and dest.suffix=='.md' and unquote(fragment) not in anchors(dest.read_text('utf8')): reason='missing heading anchor'
            if reason: local.append(dict(file=str(path.relative_to(root)),target=target,reason=reason))
    http=list(ThreadPoolExecutor(max_workers=8).map(probe,sorted(urls))) if external else []
    return dict(markdown_files=len(fs),links=count,local_errors=local,external_urls=len(urls),http_results=http)

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--external',action='store_true'); parser.add_argument('--report',type=Path); args=parser.parse_args()
    result=audit(external=args.external)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    for error in result['local_errors']: print(error)
    print(f"DOCUMENTATION {'FAIL' if result['local_errors'] else 'PASS'}: {result['markdown_files']} Markdown files; {result['links']} links; {len(result['local_errors'])} local errors")
    if args.external:
        for entry in result['http_results']:
            if entry['status'] != 200: print('HTTP CHECK:',entry)
    return bool(result['local_errors'])

if __name__=='__main__': raise SystemExit(main())
