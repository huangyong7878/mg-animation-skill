"""Fail-closed factual claim gate and optional citation-quote URL verification.

This does NOT independently judge factual truth. A human/research agent must
review claim meaning and evidence. Automated checks enforce provenance and
source-quote integrity; fetch mode verifies live webpages contain the quote.
"""
import argparse
import json
import re
import urllib.request
import urllib.parse
import socket
import ipaddress
from html.parser import HTMLParser
from pathlib import Path

class PlainText(HTMLParser):
    def __init__(self):super().__init__();self.txt=[]
    def handle_data(self,data):self.txt.append(data)

def normalize(s):return re.sub(r'\s+','',s).casefold()

def safe_public_http_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only public HTTP(S) source URLs without credentials are permitted')
    if parsed.port not in (None,80,443):
        raise ValueError('Unusual URL ports are disallowed')
    addrs=socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
    for info in addrs:
        address=ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ValueError('Non-public IP / local network source URL blocked')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('HTTP redirects are blocked in evidence checking')

def check(data,fetch=False):
    issues=[];claims=data.get('claims',[])
    lookup={}
    for c in claims:
        cid=c.get('id','')
        if not cid or cid in lookup:issues.append(f'Invalid or duplicate claim id: {cid!r}')
        lookup[cid]=c
        if c.get('status')!='verified':issues.append(f'{cid}: status must be verified (review not completed)')
        evidence=c.get('evidence',[])
        if not evidence:issues.append(f'{cid}: no evidence')
        for ei,ref in enumerate(evidence):
            url=ref.get('url','')
            quote=ref.get('quote','')
            if not re.match(r'^https?://[^/\s]+',url):issues.append(f'{cid}: evidence {ei} needs http(s) URL')
            if len(quote.strip())<8:issues.append(f'{cid}: evidence {ei} needs meaningful verbatim quote')
            if fetch and url.startswith(('https://','http://')):
                try:
                    safe_public_http_url(url)
                    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ResearchVerifier/1.0)'})
                    opener=urllib.request.build_opener(NoRedirect)
                    with opener.open(req,timeout=12) as resp:
                        body=resp.read(2_000_000).decode('utf-8','replace')
                    parser=PlainText();parser.feed(body)
                    if normalize(quote) not in normalize(' '.join(parser.txt)):
                        issues.append(f'{cid}: quote not found at {url} (possibly PDF, dynamic page or stale source)')
                except Exception as exc:
                    issues.append(f'{cid}: source retrieval failed for {url}: {exc}')
    for i,scene in enumerate(data.get('scenes',[])):
        if not scene.get('factual',False):continue
        ids=scene.get('claim_ids',[])
        if not ids:issues.append(f'scene {i}: factual=true but claim_ids empty')
        for cid in ids:
            if cid not in lookup:issues.append(f'scene {i}: unknown claim_id {cid}')
    return issues

def main():
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('--fetch-sources',action='store_true')
    p.add_argument('--report',default=None);args=p.parse_args()
    data=json.loads(Path(args.scene).read_text(encoding='utf-8'))
    errs=check(data,args.fetch_sources)
    report={'passed':not errs,'issues':errs,'mode':'source-quote-fetch' if args.fetch_sources else 'metadata-gate',
            'disclaimer':'Does not independently verify truth or evidence relevance. Human/AI research required.'}
    if args.report:
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if errs:
        for e in errs:print('BLOCK:',e)
        raise SystemExit(2)
    print('PASS: citation/verification gate (not independent truth checking)')
if __name__=='__main__':main()
