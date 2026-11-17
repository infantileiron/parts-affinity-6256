import json,hashlib
from datetime import datetime,timezone
from itertools import combinations
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.models.entities import Station,SummaryReport
from src.services.business import dump
def _now():return datetime.now(timezone.utc).isoformat()
def normalize_combos(combos):
 # 输入为 [{parts:[...],count:n}]，统一为排序元组键
 out={}
 for c in combos:
  key=tuple(sorted(set(c['parts'])))
  if key in out:raise HTTPException(422,'存在重复组合：'+'、'.join(key))
  out[key]=int(c['count'])
 return out
def checksum_of(station_code,cycle,equipment,valid_jobs,combos,note=''):
 payload={'station_code':station_code,'cycle':cycle,'equipment':equipment,'valid_jobs':valid_jobs,
  'combos':[{'parts':list(k),'count':v} for k,v in sorted(combos.items())],'note':note}
 return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def validate_combos(valid_jobs,combos):
 # 矛盾计数拒收：任何组合计数不能超过有效作业数；子集计数不得小于超集
 for key,count in combos.items():
  if count<=0:raise HTTPException(422,'组合计数必须为正整数：'+'、'.join(key))
  if count>valid_jobs:raise HTTPException(422,'组合 %s 的计数 %d 超过有效作业数 %d'%('、'.join(key),count,valid_jobs))
 for key,count in combos.items():
  items=list(key)
  for size in range(1,len(items)):
   for sub in combinations(items,size):
    sub_key=tuple(sorted(sub))
    sub_count=combos.get(sub_key)
    # 缺项不当零：未上报的子集不参与矛盾判断；显式上报才比较
    if sub_count is not None and sub_count<count:
     raise HTTPException(422,'矛盾计数：组合 %s(%d次) 是 %s(%d次) 的子集，子集计数不得更小'%('、'.join(sub_key),sub_count,'、'.join(key),count))
def ensure_station(s,code,name=None):
 row=s.query(Station).filter_by(code=code).first()
 if not row:
  # 汇总导入即分站首次接入：以编码自动登记，可随后在分站目录维护名称
  row=Station(code=code,name=name or code,created=_now());s.add(row)
  try:s.commit()
  except IntegrityError:s.rollback();row=s.query(Station).filter_by(code=code).first()
 return row
def import_report(s,data):
 combos=normalize_combos([c.model_dump() for c in data.combos])
 validate_combos(data.valid_jobs,combos)
 checksum=checksum_of(data.station_code,data.cycle,data.equipment,data.valid_jobs,combos,data.note)
 ensure_station(s,data.station_code)
 scope=dict(station_code=data.station_code,cycle=data.cycle,equipment=data.equipment)
 # 重试不重复计入：同校验和直接返回既有单据
 same=s.query(SummaryReport).filter_by(**scope,checksum=checksum).first()
 if same:return dump(same),True
 pending=s.query(SummaryReport).filter_by(**scope,state='pending').first()
 active=s.query(SummaryReport).filter_by(**scope,state='active').first()
 if pending:
  # 待核对单据的修订：原地替换而非累加，版本不变
  pending.valid_jobs=data.valid_jobs;pending.combo_counts=[{'parts':list(k),'count':v} for k,v in sorted(combos.items())]
  pending.checksum=checksum;pending.note=data.note;pending.created=_now();r=pending
 else:
  version=(active.version+1) if active else 1
  r=SummaryReport(**scope,state='pending',version=version,valid_jobs=data.valid_jobs,
   combo_counts=[{'parts':list(k),'count':v} for k,v in sorted(combos.items())],
   checksum=checksum,supersedes_id=active.id if active else None,note=data.note,created=_now())
  s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'同站同周期同设备的汇总版本冲突，请刷新后重试')
 return dump(r),False
def activate(s,i):
 r=s.get(SummaryReport,i)
 if not r:raise HTTPException(404,'汇总单据不存在')
 if r.state=='active':return dump(r)
 if r.state=='void':raise HTTPException(409,'已作废单据不能生效，请重新导入修订版本')
 scope=r.station_code+'|'+r.cycle+'|'+r.equipment
 # 发布竞争：先释放同范围旧生效版本（修订替换而非累加），再条件更新保证 pending→active 单向迁移
 try:
  old=s.query(SummaryReport).filter(
   SummaryReport.station_code==r.station_code,SummaryReport.cycle==r.cycle,
   SummaryReport.equipment==r.equipment,SummaryReport.state=='active',SummaryReport.id!=r.id).all()
  for prev in old:prev.state='void';prev.active_scope=None
  updated=s.query(SummaryReport).filter(SummaryReport.id==i,SummaryReport.state=='pending').update(
   {'state':'active','activated':_now(),'active_scope':scope},synchronize_session=False)
  if updated==0:s.rollback();raise HTTPException(409,'单据状态已变化，生效失败，请刷新后重试')
  s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'该站同周期已有生效汇总，发布竞争失败，请核对后再生效')
 s.refresh(r)
 return dump(r)
def combo_map(report):
 return {tuple(sorted(c['parts'])):int(c['count']) for c in report.combo_counts}
