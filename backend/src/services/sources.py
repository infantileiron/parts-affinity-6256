from fastapi import HTTPException
from src.models.entities import Job,SummaryReport
from src.services.summaries import combo_map
def _scope_match(value,allowed):
 return not allowed or value in allowed
def select_local(s,equipment,station_codes,cycles):
 q=s.query(Job)
 rows=[r for r in q.order_by(Job.id).all()
  if (equipment=='全部' or r.equipment==equipment)
  and _scope_match(r.station_code,station_codes)
  and _scope_match(r.cycle,cycles)]
 return rows
def select_active_summaries(s,equipment,station_codes,cycles):
 q=s.query(SummaryReport).filter_by(state='active')
 return [r for r in q.order_by(SummaryReport.id).all()
  if (equipment=='全部' or r.equipment==equipment)
  and _scope_match(r.station_code,station_codes)
  and _scope_match(r.cycle,cycles)]
def detect_overlap(local_rows,reports):
 # 明细与汇总范围重叠时阻止混算：同站同周期即判重，不静默去重
 covered={(r.station_code,r.cycle) for r in reports}
 for job in local_rows:
  if job.station_code and job.cycle and (job.station_code,job.cycle) in covered:
   raise HTTPException(409,'范围重叠：分站 %s 周期 %s 同时存在本地明细与生效汇总，不能混算；请改用单一来源或收窄范围'%(job.station_code,job.cycle))
def build_snapshot(s,data):
 # 同一事务内冻结完整来源版本：只读 active 汇总，不读 pending（避免半份汇总）
 use_local=data.source in ('local','combined')
 use_summary=data.source in ('summary','combined')
 local_rows=select_local(s,data.equipment,data.station_codes,data.cycles) if use_local else []
 reports=select_active_summaries(s,data.equipment,data.station_codes,data.cycles) if use_summary else []
 if use_local and use_summary:detect_overlap(local_rows,reports)
 local=[{'id':j.id,'code':j.code,'equipment':j.equipment,'parts':list(j.parts or []),
         'station_code':j.station_code,'cycle':j.cycle} for j in local_rows if j.parts]
 summary_sources=[];extra_counts={};total_summary_jobs=0
 for r in reports:
  counts=combo_map(r);summary_sources.append({'source':'summary:%d'%r.id,'station_code':r.station_code,
   'cycle':r.cycle,'equipment':r.equipment,'version':r.version,'report_id':r.id,
   'valid_jobs':r.valid_jobs,'checksum':r.checksum})
  total_summary_jobs+=r.valid_jobs
  for combo,count in counts.items():extra_counts[combo]=extra_counts.get(combo,0)+count
 total_n=len(local)+total_summary_jobs
 manifest={'source':data.source,'equipment':data.equipment,
  'station_codes':data.station_codes or [],'cycles':data.cycles or [],
  'local_job_ids':[j['id'] for j in local],
  'summary_versions':[{'report_id':x['report_id'],'version':x['version'],'checksum':x['checksum']} for x in summary_sources],
  'local_transactions':len(local),'summary_jobs':total_summary_jobs,'total_valid_jobs':total_n}
 snapshot={'local':local,'summary_sources':summary_sources,'extra_counts':{','.join(k):v for k,v in extra_counts.items()},'total_n':total_n}
 return manifest,snapshot
def reconcile(s,run):
 # 逐站对账：历史批次保持原值，只展示冻结快照中的来源构成
 snap=run.snapshot or {};manifest=run.source_manifest or {}
 by_station={}
 for job in snap.get('local',[]):
  key=job.get('station_code') or 'UNSCOPED'
  slot=by_station.setdefault(key,{'station_code':key,'local_transactions':0,'summary_jobs':0,'reports':[]})
  slot['local_transactions']+=1
 for src in snap.get('summary_sources',[]):
  slot=by_station.setdefault(src['station_code'],{'station_code':src['station_code'],'local_transactions':0,'summary_jobs':0,'reports':[]})
  slot['summary_jobs']+=src['valid_jobs']
  slot['reports'].append({'report_id':src['report_id'],'cycle':src['cycle'],'equipment':src['equipment'],
                          'version':src['version'],'valid_jobs':src['valid_jobs'],'checksum':src['checksum']})
 return {'run_id':run.id,'source':manifest.get('source'),'total_valid_jobs':snap.get('total_n',0),
         'stations':[by_station[k] for k in sorted(by_station)]}
