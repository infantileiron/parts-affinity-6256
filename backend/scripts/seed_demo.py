import random
from src.config.database import Base,engine,Session
from src.models.entities import User,Job,Station,SummaryReport
from src.constants.enums import PARTS,EQUIPMENT
from src.utils.security import hash_password
from src.schemas.summary import SummaryInput,Combo
from src.services.summaries import import_report,activate
def seed():
 Base.metadata.create_all(engine);rng=random.Random(3108)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  for i in range(180):
   code=f'YH-1115-{i+1:03}';equipment=EQUIPMENT[i%3]
   items=set(rng.sample(list(PARTS),rng.randint(1,3)))
   if i%3==0:items.update(['轴承','润滑脂'])
   if i%4==0:items.update(['密封圈','垫片'])
   if i%5==0:items.update(['滤芯','清洗剂'])
   if not s.query(Job).filter_by(code=code).first():s.add(Job(code=code,equipment=equipment,parts=sorted(items),note='远航维修策划组已核对作业用件，仅记录是否使用，不推算数量'))
  s.commit()
  # 演示分站：一份待核对、一份生效；自然键幂等，重复执行不产生重复版本
  for code,name in (('ST-NORTH','北港维修分站'),('ST-SOUTH','南港维修分站')):
   if not s.query(Station).filter_by(code=code).first():s.add(Station(code=code,name=name))
  s.commit()
  if not s.query(SummaryReport).filter_by(station_code='ST-NORTH',cycle='2026-W45').first():
   r,_=import_report(s,SummaryInput(station_code='ST-NORTH',cycle='2026-W45',equipment='泵组',valid_jobs=24,
    combos=[Combo(parts=['轴承'],count=18),Combo(parts=['润滑脂'],count=15),Combo(parts=['密封圈'],count=11),
            Combo(parts=['轴承','润滑脂'],count=12),Combo(parts=['润滑脂','密封圈'],count=8),
            Combo(parts=['轴承','润滑脂','密封圈'],count=7)],note='北港分站周度汇总，仅含有效作业组合计数'))
   activate(s,r['id'])
  if not s.query(SummaryReport).filter_by(station_code='ST-SOUTH',cycle='2026-W45').first():
   import_report(s,SummaryInput(station_code='ST-SOUTH',cycle='2026-W45',equipment='压缩机',valid_jobs=16,
    combos=[Combo(parts=['滤芯'],count=10),Combo(parts=['传感器'],count=9),Combo(parts=['滤芯','传感器'],count=7)],
    note='南港分站待核对周度汇总'))
  print({'users':s.query(User).count(),'jobs':s.query(Job).count(),
         'stations':s.query(Station).count(),'summaries':s.query(SummaryReport).count()})
if __name__=='__main__':seed()
