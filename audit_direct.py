import json,time,statistics,concurrent.futures,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,urljoin
import requests
import argparse
ap=argparse.ArgumentParser()
ap.add_argument("--out",default="audit")
args=ap.parse_args()
OUT=Path(args.out)
S=requests.Session();S.headers['User-Agent']='Mozilla/5.0'
QUERIES=[('电视剧','兰香如故'),('电影','流浪地球2'),('动漫','斗罗大陆')]
def fetch(url,cap=10_000_000):
 t=time.monotonic()
 with requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=(5,9),stream=True) as r:
  r.raise_for_status();first=time.monotonic()-t;data=bytearray()
  for b in r.iter_content(65536):
   data.extend(b)
   if len(data)>cap:raise ValueError('size_limit')
   if time.monotonic()-t>20:raise TimeoutError('total_deadline')
  return bytes(data),time.monotonic()-t,first,r.url

def parse_catalog(b):
 try:
  d=json.loads(b);a=d.get('list',[])
  return [{'name':v.get('vod_name',''),'groups':list(zip(v.get('vod_play_from','').split('$$$'),v.get('vod_play_url','').split('$$$')))} for v in a]
 except (ValueError,AttributeError):
  return [{'name':v.findtext('name'),'groups':[(dd.get('flag',''),dd.text or '') for dd in v.findall('.//dd')]} for v in ET.fromstring(b).findall('.//video')]
def request_url(api,query):
 s=urlsplit(api);q=dict(parse_qsl(s.query));q.update(ac='detail',wd=query)
 return urlunsplit((s.scheme,s.netloc,s.path,urlencode(q),''))
def search(item):
 api=item['api'];o={**item,'queries':[]}
 for genre,q in QUERIES:
  r={'genre':genre,'query':q,'attempts':[],'matches':[]}
  for i in range(2):
   try:
    b,t,_,_=fetch(request_url(api,q));a=parse_catalog(b)
    matches=[v for v in a if v['name']==q]
    r['attempts'].append({'ok':True,'seconds':round(t,3),'exact_matches':len(matches)})
    if matches:r['matches']=matches[:1]
   except Exception as e:r['attempts'].append({'ok':False,'error':type(e).__name__+': '+str(e)[:130]})
  o['queries'].append(r)
 return o
inv=json.load(open(OUT/'source-audit.json'));spec={}
for e in inv['sites']:
 if e['type'] in [0,1] and str(e['api']).startswith(('http://','https://')):
  key=(e['type'],e['api']);spec.setdefault(key,{'name':e['name'],'api':e['api'],'type':e['type'],'configs':[]})['configs'].append(e['config'])
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 results=list(ex.map(search,spec.values()))
json.dump(results,open(OUT/'direct-search.json','w'),ensure_ascii=False,indent=2)
print('search_done',len(results),flush=True)
for r in results:print(r['name'],[(q['genre'],sum(a['ok'] for a in q['attempts']),bool(q['matches'])) for q in r['queries']],flush=True)
# Benchmark distinct providers, preferring JSON only when both protocols passed. Catalog tests cover both protocols.
providers={}
for r in results:
 key=urlsplit(r['api']).netloc
 score=sum(len(q['matches']) for q in r['queries'])
 if key not in providers or (score,r['type'])>(providers[key][0],providers[key][1]['type']):providers[key]=(score,r)
def playlist(u,depth=0):
 if depth>4:raise ValueError('playlist recursion')
 b,t,_,actual=fetch(u);text=b.decode('utf-8-sig')
 if '#EXTM3U' not in text:raise ValueError('not HLS playlist')
 lines=[s.strip() for s in text.splitlines() if s.strip()]
 for i,l in enumerate(lines):
  if l.startswith('#EXT-X-STREAM-INF'):return playlist(urljoin(actual,lines[i+1]),depth+1)
 segs=[];dur=None
 for l in lines:
  if l.startswith('#EXTINF:'):dur=float(l.split(':',1)[1].split(',')[0])
  elif not l.startswith('#') and dur is not None:segs.append((urljoin(actual,l),dur));dur=None
 return segs
media=[]
for _,r in providers.values():
 for q in r['queries']:
  if not q['matches']:continue
  m={'provider':r['name'],'api':r['api'],'type':r['type'],'genre':q['genre'],'query':q['query'],'samples':[],'errors':[]}
  groups=q['matches'][0]['groups'];g=next((g for n,g in groups if 'm3u8' in n.lower()),None)
  if not g:continue
  eps=[x.split('$',1) for x in g.split('#') if '$' in x];m['episodes']=len(eps);m['episode']=eps[0][0];m['playlist']=eps[0][1]
  try:
   t=time.monotonic();segs=playlist(m['playlist']);m['playlist_seconds']=round(time.monotonic()-t,3)
   pos=0;idx=0
   for i,(_,d) in enumerate(segs):
    pos+=d
    if pos>=600:idx=i;break
   for rnd in range(2):
    for u,d in segs[idx:idx+3]:
     try:
      b,t,first,final=fetch(u)
      # Reject ordinary HTML/JSON error bodies masquerading as video.
      if b.lstrip().startswith((b'<!DOCTYPE',b'<html',b'{"')):raise ValueError('nonmedia response')
      m['samples'].append({'round':rnd+1,'seconds':round(t,4),'bytes':len(b),'media_seconds':d,'mbps':round(len(b)*8/t/1e6,3),'headroom':round(d/t,3),'host':urlsplit(final).netloc})
     except Exception as e:m['errors'].append(type(e).__name__+': '+str(e)[:130])
   p=subprocess.run(['ffprobe','-v','error','-rw_timeout','8000000','-analyzeduration','2000000','-probesize','1000000','-show_entries','stream=codec_type,codec_name,width,height','-of','json',m['playlist']],capture_output=True,text=True,timeout=22)
   m['probe']={'returncode':p.returncode,'streams':json.loads(p.stdout or '{}').get('streams',[]),'stderr':p.stderr[-350:]}
  except Exception as e:m['errors'].append(type(e).__name__+': '+str(e)[:130])
  sam=m['samples']
  if sam:m['summary']={'success':len(sam),'expected':6,'median_mbps':round(statistics.median(x['mbps'] for x in sam),3),'median_headroom':round(statistics.median(x['headroom'] for x in sam),3),'min_headroom':min(x['headroom'] for x in sam),'below_realtime':sum(x['headroom']<1 for x in sam)}
  media.append(m);json.dump(media,open(OUT/'media-tests.json','w'),ensure_ascii=False,indent=2)
  print('media',m['provider'],m['genre'],m.get('summary'),m.get('probe',{}).get('returncode'),flush=True)
print('all_done',flush=True)
