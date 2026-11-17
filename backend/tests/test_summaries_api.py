import pytest
from fastapi import HTTPException
def _summary(station='st-a',cycle='2026-W46',equipment='泵组',n=10,combos=None):
 return {'station_code':station,'cycle':cycle,'equipment':equipment,'valid_jobs':n,
  'combos':combos or [{'parts':['轴承'],'count':8},{'parts':['润滑脂'],'count':6},{'parts':['轴承','润滑脂'],'count':5}]}
def test_station_auto_registered_on_import(client,auth):
 h=auth()
 r=client.post('/summaries/import',json=_summary(),headers=h)
 assert r.status_code==200 and r.json()['state']=='pending'
 assert client.get('/stations',headers=h).json()[0]['code']=='st-a'
def test_retry_import_is_idempotent(client,auth):
 h=auth();payload=_summary()
 first=client.post('/summaries/import',json=payload,headers=h).json()
 second=client.post('/summaries/import',json=payload,headers=h).json()
 assert first['id']==second['id'] and second['deduplicated'] is True
 rows=client.get('/summaries',headers=h).json()
 assert len(rows)==1
def test_contradictory_counts_rejected(client,auth):
 h=auth()
 bad=_summary(station='st-b',n=5,combos=[{'parts':['轴承'],'count':2},{'parts':['轴承','润滑脂'],'count':4}])
 r=client.post('/summaries/import',json=bad,headers=h)
 assert r.status_code==422 and '矛盾计数' in r.json()['detail']
 over=_summary(station='st-c',n=3,combos=[{'parts':['轴承'],'count':9}])
 r=client.post('/summaries/import',json=over,headers=h)
 assert r.status_code==422 and '超过有效作业数' in r.json()['detail']
def test_four_piece_combo_rejected(client,auth):
 h=auth();bad=_summary(station='st-d',combos=[{'parts':['轴承','润滑脂','密封圈','垫片'],'count':2}])
 assert client.post('/summaries/import',json=bad,headers=h).status_code==422
def test_revision_replaces_not_accumulates(client,auth):
 h=auth()
 first=client.post('/summaries/import',json=_summary(),headers=h).json()
 client.post(f"/summaries/{first['id']}/activate",headers=h)
 revised=_summary(n=12,combos=[{'parts':['轴承'],'count':9},{'parts':['润滑脂'],'count':7},{'parts':['轴承','润滑脂'],'count':6}])
 second=client.post('/summaries/import',json=revised,headers=h).json()
 assert second['version']==2 and second['supersedes_id']==first['id'] and second['state']=='pending'
 client.post(f"/summaries/{second['id']}/activate",headers=h)
 rows=client.get('/summaries?station_code=st-a',headers=h).json()
 active=[x for x in rows if x['state']=='active'];void=[x for x in rows if x['state']=='void']
 assert len(active)==1 and active[0]['id']==second['id'] and len(void)==1
def test_activation_is_conditional_and_reactivation_guarded(client,auth):
 h=auth()
 rid=client.post('/summaries/import',json=_summary(station='st-e'),headers=h).json()['id']
 assert client.post(f'/summaries/{rid}/activate',headers=h).json()['state']=='active'
 # 重复生效幂等
 assert client.post(f'/summaries/{rid}/activate',headers=h).json()['state']=='active'
 # 作废后不可再生效
 from src.config.database import Session
 from src.models.entities import SummaryReport
 with Session() as s:
  row=s.get(SummaryReport,rid);row.state='void';s.commit()
 assert client.post(f'/summaries/{rid}/activate',headers=h).status_code==409
def test_pending_summary_not_visible_to_mining(client,auth):
 h=auth()
 client.post('/summaries/import',json=_summary(station='st-p',cycle='2026-W48'),headers=h)
 r=client.post('/runs',json={'name':'待核对不参与','source':'summary'},headers=h)
 assert r.status_code==422  # 无生效来源，有效作业不足
def test_viewer_cannot_import_or_activate(client,auth):
 h=auth('viewer')
 assert client.post('/summaries/import',json=_summary(station='st-v'),headers=h).status_code==403
def test_bad_cycle_and_station_format(client,auth):
 h=auth();bad=_summary();bad['cycle']='2026/11'
 assert client.post('/summaries/import',json=bad,headers=h).status_code==422
 bad['cycle']='2026-W46';bad['station_code']='a'
 assert client.post('/summaries/import',json=bad,headers=h).status_code==422
