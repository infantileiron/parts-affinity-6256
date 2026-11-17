import math,json,hashlib
from itertools import combinations
VERSION='apriori-max3-v2-weighted'
# 事务型挖掘（本地明细）：每张含备件的有效作业是一个事务，重复备件去重
def mine(rows,min_support=.15,min_confidence=.6,min_lift=1):
 transactions=[frozenset(r['parts']) for r in rows if r.get('parts')]
 result=mine_weighted(transactions,len(transactions),min_support,min_confidence,min_lift)
 result['excluded']=len(rows)-len(transactions)
 return result
def _check_thresholds(min_support,min_confidence,min_lift,n):
 if n<2:raise ValueError('至少需要2条含备件的有效维保作业')
 if not 0<min_support<=1 or not 0<min_confidence<=1 or min_lift<0:raise ValueError('无效阈值')
def _combo_key(parts):return frozenset(parts)
def build_local_counts(transactions):
 # 从事务明细生成全部1-3件组合计数（仅出现过的组合，缺项不写零）
 counts={}
 for t in transactions:
  items=sorted(t)
  for size in range(1,min(3,len(items))+1):
   for combo in combinations(items,size):
    key=frozenset(combo);counts[key]=counts.get(key,0)+1
 return counts
def merge_counts(sources):
 # 加权合并：各来源同组合计数相加；缺项不当零，只在显式上报时计入
 merged={};provenance={}
 for source_id,counts in sources:
  for combo,count in counts.items():
   merged[combo]=merged.get(combo,0)+count
   provenance.setdefault(combo,[]).append({'source':source_id,'count':count})
 return merged,provenance
def mine_weighted(transactions,total_n,min_support=.15,min_confidence=.6,min_lift=1,extra_counts=None,sources=None):
 # transactions：本地明细事务（可为空）；extra_counts：生效汇总的加权组合计数（键可为元组或frozenset）
 _check_thresholds(min_support,min_confidence,min_lift,total_n)
 if extra_counts:extra_counts={_combo_key(k):v for k,v in extra_counts.items()}
 counts=build_local_counts(transactions)
 source_breakdown=[{'source':'local:detail','transactions':len(transactions)}]
 if extra_counts:
  for combo,count in extra_counts.items():counts[combo]=counts.get(combo,0)+count
  source_breakdown.extend(sources or [])
 minimum=math.ceil(total_n*min_support-1e-12)
 # 逐层频繁项集（最大长度3），候选先查全部子集是否频繁，缺项视为不频繁而非零通过
 frequent_counts={};level=[]
 universe=sorted({p for combo in counts for p in combo})
 for part in universe:
  key=frozenset([part]);count=counts.get(key,0)
  if count>=minimum:frequent_counts[key]=count;level.append(key)
 for size in (2,3):
  joined={a|b for a in level for b in level if len(a|b)==size}
  # 汇总可能只上报多件组合而缺报子集：显式上报且达阈值的组合直接入候选，不被缺项误判为零
  reported={c for c in counts if len(c)==size and counts[c]>=minimum}
  candidates=reported|{c for c in joined if all(frozenset(s) in frequent_counts for s in combinations(sorted(c),size-1))}
  level=[]
  for c in sorted(candidates,key=lambda c:tuple(sorted(c))):
   count=counts.get(c,0)  # 汇总未上报的组合不读零：未在counts中即不满足最小计数
   if count>=minimum:frequent_counts[c]=count;level.append(c)
 rules=[]
 for itemset,count in frequent_counts.items():
  if len(itemset)<2:continue
  for size in range(1,len(itemset)):
   for a_tuple in combinations(sorted(itemset),size):
    a=frozenset(a_tuple);b=itemset-a
    ca=frequent_counts.get(a);cb=frequent_counts.get(b)
    # 矛盾防护：前件/后件计数缺失则无法计算，跳过而不是补零
    if not ca or not cb:continue
    support=count/total_n;confidence=count/ca;lift=confidence/(cb/total_n)
    if confidence+1e-12>=min_confidence and lift+1e-12>=min_lift:
     rules.append({'signature':','.join(sorted(a))+'->'+','.join(sorted(b)),'antecedent':sorted(a),'consequent':sorted(b),'count':count,'support':support,'confidence':confidence,'lift':lift})
 rules.sort(key=lambda r:(-r['lift'],-r['confidence'],-r['support'],r['signature']))
 frequent=[{'items':sorted(k),'count':v,'support':v/total_n} for k,v in sorted(frequent_counts.items(),key=lambda kv:(len(kv[0]),sorted(kv[0])))]
 return dict(valid_jobs=total_n,minimum_count=minimum,frequent=frequent,rules=rules,version=VERSION,
  checksum=hashlib.sha256(json.dumps({'n':total_n,'counts':{','.join(sorted(k)):v for k,v in counts.items()}},sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
  sources=source_breakdown,
  method='加权Apriori最大项集长度3；本地明细按事务计数、生效分站汇总按组合计数加权合并，缺项不当零；support=count(A∪B)/N；confidence=count(A∪B)/count(A)；lift=confidence/support(B)。关联不代表必须联换，需核对设备、兼容性与备件数量。')
