from src.schemas.summary import SummaryInput,Combo
from src.services.summaries import import_report,activate
from src.models.entities import SummaryReport
from fastapi import HTTPException
def _payload(n=10):
 return SummaryInput(station_code='st-r',cycle='2026-W46',equipment='泵组',valid_jobs=n,
  combos=[Combo(parts=['轴承'],count=8),Combo(parts=['润滑脂'],count=6),Combo(parts=['轴承','润滑脂'],count=5)])
def test_publish_race_second_activation_replaces_first(client,auth):
 h=auth()
 first=client.post('/summaries/import',json=_payload().model_dump(),headers=h).json()
 client.post(f"/summaries/{first['id']}/activate",headers=h)
 # 同范围第二份修订进入待核对
 revised=SummaryInput(station_code='st-r',cycle='2026-W46',equipment='泵组',valid_jobs=12,
  combos=[Combo(parts=['轴承'],count=9),Combo(parts=['润滑脂'],count=7),Combo(parts=['轴承','润滑脂'],count=6)])
 from src.config.database import Session
 with Session() as s:
  r2,dedup=import_report(s,revised)
  out=activate(s,r2['id'])
  active=s.query(SummaryReport).filter_by(state='active').all()
  assert len(active)==1 and active[0].id==r2['id']
  assert s.get(SummaryReport,first['id']).state=='void'
 # 旧生效版本不可再次生效
 with Session() as s:
  old=s.get(SummaryReport,first['id'])
  try:activate(s,old.id);assert False
  except HTTPException as e:assert e.status_code==409
def test_activation_is_conditional_against_concurrent_state(client,auth):
 # 两个独立会话同时生效同一待核对单据，只有一个能成功
 from src.config.database import Session
 with Session() as s1:
  r,_=import_report(s1,_payload());rid=r['id']
 with Session() as s1,Session() as s2:
  out1=activate(s1,rid)
  try:
   activate(s2,rid);raced=False
  except HTTPException as e:
   raced=e.status_code==409
  assert raced is True or out1['state']=='active'
 with Session() as s:
  assert s.query(SummaryReport).filter_by(state='active').count()==1
def test_missing_subset_api_keeps_itemset_but_no_fake_rule(client,auth):
 h=auth()
 # 分站只上报二件套，缺报单件：导入合法（子集未上报不参与矛盾判断）
 r=client.post('/summaries/import',headers=h,json={'station_code':'st-m','cycle':'2026-W46','equipment':'风机',
  'valid_jobs':10,'combos':[{'parts':['垫片','滤芯'],'count':8}]})
 assert r.status_code==200
 rid=r.json()['id'];client.post(f'/summaries/{rid}/activate',headers=h)
 run=client.post('/runs',headers=h,json={'name':'缺项验证','source':'summary','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 from tests.test_mining_api import _process
 _process(run['id'])
 detail=client.get(f"/runs/{run['id']}",headers=h).json()
 assert detail['result']['valid_jobs']==10
 assert [f['items'] for f in detail['result']['frequent']]==[['垫片','滤芯']]
 assert detail['result']['rules']==[]  # 缺项不补零，不伪造规则
def test_weighted_merge_combines_two_station_counts(client,auth):
 h=auth()
 for st,n,single in (('st-1',10,8),('st-2',20,15)):
  r=client.post('/summaries/import',headers=h,json={'station_code':st,'cycle':'2026-W46','equipment':'泵组',
   'valid_jobs':n,'combos':[{'parts':['轴承'],'count':single}]}).json()
  client.post(f"/summaries/{r['id']}/activate",headers=h)
 run=client.post('/runs',headers=h,json={'name':'两站加权','source':'summary','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 from tests.test_mining_api import _process
 _process(run['id'])
 detail=client.get(f"/runs/{run['id']}",headers=h).json()
 assert detail['result']['valid_jobs']==30  # 分母为两站有效作业之和
 single=next(f for f in detail['result']['frequent'] if f['items']==['轴承'])
 assert single['count']==23  # 8+15 加权合并
 rec=client.get(f"/runs/{run['id']}/reconciliation",headers=h).json()
 assert {x['station_code'] for x in rec['stations']}=={'st-1','st-2'}
