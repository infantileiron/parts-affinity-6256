import os,time,json,logging
from pathlib import Path
import redis
from src.config.database import Session
from src.models.entities import MiningRun,AssociationRule
from src.services.analysis import mine_weighted
ARTIFACTS_DIR=os.environ.get('ARTIFACTS_DIR','/artifacts')
def run_once(s,row):
 snap=row.snapshot
 if not snap:raise ValueError('批次缺少冻结来源快照')
 transactions=[frozenset(j['parts']) for j in snap.get('local',[]) if j.get('parts')]
 extra_counts={tuple(k.split(',')) if isinstance(k,str) else tuple(k):v for k,v in snap.get('extra_counts',{}).items()}
 result=mine_weighted(transactions,snap['total_n'],row.min_support,row.min_confidence,row.min_lift,
  extra_counts=extra_counts,sources=snap.get('summary_sources'))
 s.query(AssociationRule).filter_by(run_id=row.id).delete()
 for rule in result['rules']:s.add(AssociationRule(run_id=row.id,**rule))
 row.result=result;row.state='done'
 Path(ARTIFACTS_DIR).mkdir(parents=True,exist_ok=True)
 Path(os.path.join(ARTIFACTS_DIR,str(row.id)+'.json')).write_text(
  json.dumps({**result,'snapshot':snap,'manifest':row.source_manifest},ensure_ascii=False))
def process_message(s,run_id):
 row=s.get(MiningRun,int(run_id))
 # 重试不重复计入：仅 queued 可执行；done/failed/running 的重投消息直接丢弃
 if not row or row.state!='queued':return False
 row.state='running';s.commit()
 try:run_once(s,row)
 except Exception as e:row.state='failed';row.error=str(e)
 s.commit()
 return True
def main():
 r=redis.Redis.from_url(os.environ['REDIS_URL'])
 with Session() as recovery:
  for pending in recovery.query(MiningRun).filter(MiningRun.state.in_(['queued','running'])).all():pending.state='queued';r.rpush('affinity:runs',pending.id)
  recovery.commit()
 while True:
  Path('/tmp/heartbeat').touch()
  try:
   item=r.blpop('affinity:runs',timeout=3)
   if not item:continue
   with Session() as s:process_message(s,item[1])
  except Exception:logging.exception('worker');time.sleep(2)
if __name__=='__main__':main()
