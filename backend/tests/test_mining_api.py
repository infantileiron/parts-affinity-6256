def _active_summary(client,h,station,cycle,equipment,n,combos):
 r=client.post('/summaries/import',headers=h,
  json={'station_code':station,'cycle':cycle,'equipment':equipment,'valid_jobs':n,'combos':combos})
 rid=r.json()['id']
 client.post(f'/summaries/{rid}/activate',headers=h)
 return rid
def _process(run_id):
 from src.worker import process_message
 from src.config.database import Session
 with Session() as s:return process_message(s,run_id)
def test_summary_only_weighted_run_and_reconciliation(client,auth):
 h=auth()
 _active_summary(client,h,'st-a','2026-W46','泵组',10,
  [{'parts':['轴承'],'count':8},{'parts':['润滑脂'],'count':6},{'parts':['轴承','润滑脂'],'count':5}])
 run=client.post('/runs',headers=h,json={'name':'汇总加权挖掘','source':'summary','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 assert run['source_manifest']['summary_jobs']==10 and run['snapshot']['total_n']==10
 assert _process(run['id']) is True
 detail=client.get(f"/runs/{run['id']}",headers=h).json()
 assert detail['state']=='done' and detail['result']['valid_jobs']==10
 rule=next(r for r in detail['result']['rules'] if r['signature']=='轴承->润滑脂')
 assert rule['count']==5
 rec=client.get(f"/runs/{run['id']}/reconciliation",headers=h).json()
 assert rec['total_valid_jobs']==10 and rec['stations'][0]['station_code']=='st-a'
 assert rec['stations'][0]['summary_jobs']==10
def test_combined_weighted_merge_local_and_summary(client,auth):
 h=auth()
 # 本地无 scope 明细（历史补录），与另一站汇总联用
 for i,parts in enumerate([['轴承','润滑脂'],['轴承']],1):
  client.post('/jobs',headers=h,json={'code':f'L{i:03}','equipment':'泵组','parts':parts})
 _active_summary(client,h,'st-a','2026-W46','泵组',10,
  [{'parts':['轴承'],'count':6},{'parts':['润滑脂'],'count':5},{'parts':['轴承','润滑脂'],'count':4}])
 run=client.post('/runs',headers=h,json={'name':'联用挖掘','source':'combined','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 assert run['snapshot']['total_n']==12
 assert run['snapshot']['extra_counts']['轴承']==6
 _process(run['id'])
 detail=client.get(f"/runs/{run['id']}",headers=h).json()
 pair=next(f for f in detail['result']['frequent'] if len(f['items'])==2 and set(f['items'])=={'轴承','润滑脂'})
 assert pair['count']==5  # 汇总4 + 本地1
def test_scope_overlap_blocks_mixed_calculation(client,auth):
 h=auth()
 client.post('/jobs',headers=h,json={'code':'SCOPE1','equipment':'泵组','parts':['轴承'],
  'station_code':'st-a','cycle':'2026-W46'})
 client.post('/jobs',headers=h,json={'code':'SCOPE2','equipment':'泵组','parts':['润滑脂'],
  'station_code':'st-a','cycle':'2026-W46'})
 _active_summary(client,h,'st-a','2026-W46','泵组',10,[{'parts':['轴承'],'count':8}])
 r=client.post('/runs',headers=h,json={'name':'重叠混算','source':'combined'})
 assert r.status_code==409 and '范围重叠' in r.json()['detail']
 # 单一来源仍可用
 assert client.post('/runs',headers=h,json={'name':'仅本地','source':'local'}).status_code==200
 assert client.post('/runs',headers=h,json={'name':'仅汇总','source':'summary'}).status_code==200
def test_job_requires_station_and_cycle_together(client,auth):
 h=auth()
 r=client.post('/jobs',headers=h,json={'code':'BAD1','equipment':'风机','parts':['垫片'],'station_code':'st-a'})
 assert r.status_code==422 and '分站与周期' in r.json()['detail'][0]['msg']
 ok=client.post('/jobs',headers=h,json={'code':'OK1','equipment':'风机','parts':['垫片'],'station_code':'st-a','cycle':'2026-W46'})
 assert ok.status_code==200 and ok.json()['cycle']=='2026-W46'
def test_frozen_snapshot_ignores_later_activation(client,auth):
 h=auth()
 _active_summary(client,h,'st-a','2026-W46','泵组',10,[{'parts':['轴承'],'count':8}])
 run=client.post('/runs',headers=h,json={'name':'冻结批次','source':'summary','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 # 随后修订并生效新版本
 client.post('/summaries/import',headers=h,json={'station_code':'st-a','cycle':'2026-W46','equipment':'泵组',
  'valid_jobs':20,'combos':[{'parts':['轴承'],'count':15}]})
 pending=[x for x in client.get('/summaries',headers=h).json() if x['state']=='pending'][0]
 client.post(f"/summaries/{pending['id']}/activate",headers=h)
 _process(run['id'])
 detail=client.get(f"/runs/{run['id']}",headers=h).json()
 # 历史批次保持原值：仍为冻结时的 N=10、计数8
 assert detail['result']['valid_jobs']==10
 frozen=detail['snapshot']['summary_sources'][0]
 assert frozen['valid_jobs']==10 and frozen['checksum']
def test_worker_retry_does_not_double_count(client,auth):
 h=auth()
 _active_summary(client,h,'st-a','2026-W46','泵组',10,
  [{'parts':['轴承'],'count':8},{'parts':['润滑脂'],'count':6},{'parts':['轴承','润滑脂'],'count':5}])
 run=client.post('/runs',headers=h,json={'name':'重试幂等','source':'summary','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 assert _process(run['id']) is True
 # 模拟消息重投：done 状态必须被跳过，不重复计入
 assert _process(run['id']) is False
 from src.config.database import Session
 from src.models.entities import AssociationRule
 with Session() as s:
  n_rules=s.query(AssociationRule).filter_by(run_id=run['id']).count()
 detail=client.get(f"/runs/{run['id']}",headers=h).json()
 assert detail['state']=='done' and n_rules==len(detail['result']['rules']) and n_rules>0
def test_kit_drafting_from_summary_rule_and_approval(client,auth):
 h=auth()
 _active_summary(client,h,'st-a','2026-W46','泵组',10,
  [{'parts':['轴承'],'count':8},{'parts':['润滑脂'],'count':6},{'parts':['轴承','润滑脂'],'count':5}])
 run=client.post('/runs',headers=h,json={'name':'备件包来源','source':'summary','min_support':0.1,'min_confidence':0.1,'min_lift':0}).json()
 _process(run['id'])
 rules=client.get(f"/rules?run_id={run['id']}",headers=h).json()
 kit=client.post('/kits',headers=h,json={'name':'泵组联用包','rule_id':rules[0]['id'],'note':'仅限同规格泵组，核对密封材质与数量'}).json()
 assert set(kit['parts'])==set(rules[0]['antecedent'])|set(rules[0]['consequent'])
 assert client.post(f"/kits/{kit['id']}/approve",headers=auth('admin')).json()['status']=='approved'
 assert client.post(f"/kits/{kit['id']}/approve",headers=auth('admin')).status_code==409
