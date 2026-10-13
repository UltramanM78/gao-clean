import sys,json,re,subprocess,hashlib,posixpath,time,concurrent.futures,urllib.parse,ipaddress
from pathlib import Path
import argparse
ap=argparse.ArgumentParser()
ap.add_argument("--repo",default=".")
ap.add_argument("--out",default="audit")
ap.add_argument("--ref",default="8213bb046f4dce746b5f2ddcddb13a336d0b0d60")
args=ap.parse_args()
import json5,requests
repo=Path(args.repo);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
files=git('ls-tree','-r','--name-only','-z',args.ref).decode().split('\0');files=[p for p in files if p]
blobs={p:git('show',args.ref+':'+p) for p in files if p.endswith(('.json','.js','.md','.txt','.m3u'))}
parsed={};errors={}
for p,b in blobs.items():
 if p.endswith('.json'):
  try:parsed[p]=json5.loads(b.decode('utf-8-sig'))
  except Exception as e:errors[p]=str(e)[:200]
def category(name,api):
 s=name+' '+api
 for c,words in [('网盘/磁力',['网盘','网盤','阿狸','阿里','夸克','夸搜','盘搜','盤搜','盤搜索','搜搜','磁力','PikPak','迅雷','115','UC云','AList','Ali','Pan','Wogg','Wobg']),('体育',['体育','看球','球迷','310','88看球','Kanqiu']),('直播',['直播','虎牙','斗鱼','JustLive']),('动漫/少儿/教育',['动漫','動漫','少儿','儿童','课堂','教学','启蒙','教育','急救','Anime']),('音频/音乐',['音乐','音频','听书','评书','相声','广播','MV','KTV','酷狗','有声']),('工具/元数据',['本地','Local','WebDAV','配置','推送','公众号','免费','广告','导航','商店','豆瓣','片单','预告'])]:
  if any(w.lower() in s.lower() for w in words):return c
 return '综合影视'
def localref(value,config):
 if not isinstance(value,str):return None
 v=value.split(';md5;')[0].split('?')[0]
 if v.startswith('./') or v.startswith('../'):return posixpath.normpath(posixpath.join(posixpath.dirname(config),v))
 return None
def pieces(value):
 if isinstance(value,str):
  return value.split('$$$')
 if isinstance(value,dict):
  return [p for v in value.values() for p in pieces(v)]
 if isinstance(value,list):
  return [p for v in value for p in pieces(v)]
 return []
entries=[];live=[];parse_entries=[];configfiles=[]
def walk(obj,path,config,spider=''):
 if isinstance(obj,dict):
  sp=obj.get('spider',spider)
  if isinstance(obj.get('sites'),list):
   configfiles.append(config)
   for n,s in enumerate(obj['sites']):
    if not isinstance(s,dict):continue
    api=s.get('api','');ext=s.get('ext','');jar=s.get('jar',sp)
    dep=[]
    for value in pieces([api,ext,jar]):
     if isinstance(value,str):
      ref=localref(value,config)
      if ref:dep.append({'path':ref,'exists':ref in files})
    # only literal host declarations from JS / rule objects; never execute scripts
    hosts=[]
    for value in pieces([api,ext]):
     ref=localref(value,config)
     if ref and ref in blobs:
      txt=blobs[ref].decode('utf-8','replace')
      hosts+=re.findall(r'(?:\bhost\b|\bHOST\b|\bsiteUrl\b|主页url|主域名)[\s\"\x27]*[:=]\s*[\"\x27](https?://[^\"\x27\s]+)',txt)
    if s.get('type') in [0,1,4] and isinstance(api,str) and api.startswith(('http://','https://')):hosts.append(api)
    ext_urls=[]
    if isinstance(ext,str) and ext.startswith(('http://','https://')):ext_urls.append(ext)
    fingerprint=json.dumps([s.get('type'),api,ext,jar],sort_keys=True,ensure_ascii=False)
    entries.append({'id':hashlib.sha256(fingerprint.encode()).hexdigest()[:16],'config':config,'index':n,'name':s.get('name',''),'key':s.get('key',''),'type':s.get('type'),'api':api,'category':category(s.get('name',''),str(api)),'dependencies':dep,'literal_endpoints':sorted(set(hosts)),'external_rule_urls':ext_urls,'runtime_status':'NOT_TESTED','dependency_status':'MISSING' if any(not x['exists'] for x in dep) else 'PRESENT_OR_EXTERNAL','status_note':'Plugin execution required; endpoint HTTP success is not playback success' if s.get('type')==3 else 'Awaiting protocol test'})
  for key in ['lives','parses']:
   if isinstance(obj.get(key),list):
    for item in obj[key]:
     if isinstance(item,dict):(live if key=='lives' else parse_entries).append({'config':config,'name':item.get('name',''),'url':item.get('url',''),'type':item.get('type')})
  for k,v in obj.items():
   if k not in ['sites','lives','parses']:walk(v,path+'/'+k,config,sp)
 elif isinstance(obj,list):
  for v in obj:walk(v,path,config,spider)
for p,d in parsed.items():walk(d,'',p)
# Unique public origin reachability only. No credentials, private IPs or local-network endpoints.
origins=set()
for e in entries:
 for u in e['literal_endpoints']:
  try:
   z=urllib.parse.urlsplit(u);h=z.hostname
   if not h or h in ['localhost','example.com'] or '{' in h or '@' in z.netloc:continue
   try:
    if not ipaddress.ip_address(h).is_global:continue
   except ValueError:pass
   origins.add(z.scheme+'://'+z.netloc+'/')
  except Exception:pass
summary={'upstream':'https://github.com/gaotianliuyun/gao','commit':git('rev-parse',args.ref).decode().strip(),'upstream_date':git('log','-1','--format=%cI',args.ref).decode().strip(),'audit_date':__import__('datetime').datetime.now(__import__('datetime').timezone(__import__('datetime').timedelta(hours=8))).isoformat(),'tracked_files':len(files),'json_files':sum(p.endswith('.json') for p in files),'config_files':sorted(set(configfiles)),'site_entries':len(entries),'unique_execution_specs':len({e['id'] for e in entries}),'json_parse_errors':errors,'static_only_notice':'All config entries inventoried. No Android/JAR/JS runtime available; those sources are NOT_TESTED, never declared dead merely from an HTTP result.'}
json.dump({'summary':summary,'sites':entries,'live_lists':live,'parsers':parse_entries},open(out/'source-audit.json','w'),ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False),flush=True)
print('origin_checks',len(origins),flush=True)
def check(u):
 attempts=[]
 for _ in range(2):
  start=time.monotonic()
  try:
   with requests.get(u,timeout=(4,6),stream=True,headers={'User-Agent':'Mozilla/5.0'}) as r:
    status=r.status_code;final=r.url
   attempts.append({'http_status':status,'seconds':round(time.monotonic()-start,3),'final_host':urllib.parse.urlsplit(final).hostname})
  except Exception as ex:attempts.append({'error_type':type(ex).__name__,'seconds':round(time.monotonic()-start,3)})
 return {'origin':u,'attempts':attempts,'meaning':'Origin reachability only; not source or playback validation'}
old_checks=json.load(open(out/'origin-checks.json')) if (out/'origin-checks.json').exists() else []
results=[r for r in old_checks if r['origin'] in origins]
origins-=set(r['origin'] for r in results)
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
 for i,r in enumerate(pool.map(check,sorted(origins))):
  results.append(r)
  if (i+1)%20==0:print('origins_done',i+1,flush=True)
json.dump(results,open(out/'origin-checks.json','w'),ensure_ascii=False,indent=2)
print('done',len(results),flush=True)
