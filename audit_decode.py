import json,subprocess,concurrent.futures
from pathlib import Path
import argparse
ap=argparse.ArgumentParser()
ap.add_argument("--out",default="audit")
args=ap.parse_args()
p=Path(args.out)/"media-tests.json";rs=json.load(open(p))
def run(m):
 if m['provider'].startswith('百度'):
  cmd=['ffprobe','-v','error','-rw_timeout','8000000','-allowed_extensions','ALL','-allowed_segment_extensions','ALL','-extension_picky','0','-analyzeduration','2000000','-probesize','1000000','-show_entries','stream=codec_type,codec_name,width,height','-of','json',m['playlist']]
 else:
  cmd=['ffmpeg','-nostdin','-v','error','-rw_timeout','8000000','-ss','600','-i',m['playlist'],'-t','3','-map','0:v:0','-map','0:a:0','-f','null','-']
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
  result={'returncode':r.returncode,'stderr':r.stderr[-600:]}
  if 'ffprobe' in cmd[0]:result['streams']=json.loads(r.stdout or '{}').get('streams',[]);result['note']='Retry permits actual HLS media under .jpeg suffix; previous failure was extension policy, not proof of dead source';m['probe_retry']=result
  else:result.update(offset_s=600,duration_s=3);m['decode']=result
 except Exception as e:m['validation_error']=str(e)
 return m
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rs=list(ex.map(run,rs))
json.dump(rs,open(p,'w'),ensure_ascii=False,indent=2)
for m in rs:print(m['provider'],m['genre'],m.get('decode',m.get('probe_retry',m.get('validation_error'))))
