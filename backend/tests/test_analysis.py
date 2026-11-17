import pytest
from src.services.analysis import mine,mine_weighted,build_local_counts,merge_counts
def test_legacy_transaction_mine_dedup_parts():
 rows=[{'parts':['轴承','润滑脂','轴承']},{'parts':['润滑脂']},{'parts':[]}]
 r=mine(rows,0.1,0.1,0.0)
 assert r['valid_jobs']==2 and r['excluded']==1
 singles={tuple(f['items']):f['count'] for f in r['frequent'] if len(f['items'])==1}
 assert singles[('润滑脂',)]==2 and singles[('轴承',)]==1
 assert r['version'].startswith('apriori-max3-v2')
def test_weighted_merge_adds_counts_across_stations():
 a=build_local_counts([frozenset(['轴承','润滑脂']),frozenset(['轴承'])])
 merged,prov=merge_counts([('local',a),('summary:1',{frozenset(['轴承']):5,frozenset(['轴承','润滑脂']):4})])
 assert merged[frozenset(['轴承'])]==7 and merged[frozenset(['轴承','润滑脂'])]==5
 assert {p['source'] for p in prov[frozenset(['轴承'])]}=={'local','summary:1'}
def test_weighted_mine_uses_total_n_as_denominator():
 # 汇总 10 条作业 + 本地 2 条事务，分母为 12
 tx=[frozenset(['轴承','润滑脂']),frozenset(['轴承'])]
 extra={('轴承',):6,('润滑脂',):5,('轴承','润滑脂',):4}
 r=mine_weighted(tx,12,0.1,0.1,0.0,extra_counts=extra)
 pair=[f for f in r['frequent'] if len(f['items'])==2][0]
 assert pair['count']==5 and round(pair['support'],6)==round(5/12,6)
 rule=next(x for x in r['rules'] if x['signature']=='轴承->润滑脂')
 assert rule['count']==5 and rule['confidence']==5/(6+2)
def test_missing_combo_is_not_treated_as_zero():
 # 分站只上报二件套，未报单件：二件套保留为频繁项集，但无法派生规则
 r=mine_weighted([],10,0.1,0.1,0.0,extra_counts={('垫片','滤芯'):8})
 assert [f['items'] for f in r['frequent']]==[['垫片','滤芯']]
 assert r['rules']==[]
def test_missing_subset_does_not_block_reported_superset():
 # 单件仅部分上报，显式上报的三件套仍入频繁项集，缺项不补零
 r=mine_weighted([],20,0.1,0.1,0.0,extra_counts={('轴承',):15,('轴承','润滑脂','密封圈'):9})
 items={tuple(sorted(f['items'])) for f in r['frequent']}
 assert tuple(sorted(['轴承','润滑脂','密封圈'])) in items
def test_insufficient_sample_fails():
 with pytest.raises(ValueError):mine_weighted([],1,0.1,0.1,0.0)
 with pytest.raises(ValueError):mine([{'parts':['轴承']}],0.1,0.1,0.0)
def test_threshold_too_high_returns_no_rules_not_fake_ones():
 r=mine_weighted([frozenset(['轴承']),frozenset(['润滑脂'])],2,0.9,0.9,50.0)
 assert r['rules']==[] and r['frequent']==[]
