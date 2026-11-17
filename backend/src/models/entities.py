from sqlalchemy import Column,Integer,String,Float,JSON,Text,ForeignKey,UniqueConstraint,Index
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True,nullable=False);password=Column(String(200));role=Column(String(20))
class Station(Base):
 __tablename__='stations'
 id=Column(Integer,primary_key=True);code=Column(String(40),unique=True,nullable=False);name=Column(String(100),nullable=False);created=Column(String(40))
class Job(Base):
 __tablename__='jobs'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False);equipment=Column(String(40));parts=Column(JSON);note=Column(Text,default='')
 # 本地补录：分站与周期（明细口径）；历史数据为空，视为站内本地明细且不归属任何汇总周期
 station_code=Column(String(40),nullable=True);cycle=Column(String(20),nullable=True)
 __table_args__=(Index('ix_jobs_scope','station_code','cycle'),)
class SummaryReport(Base):
 __tablename__='summary_reports'
 id=Column(Integer,primary_key=True)
 station_code=Column(String(40),nullable=False);cycle=Column(String(20),nullable=False);equipment=Column(String(40),nullable=False)
 state=Column(String(20),default='pending',nullable=False)
 version=Column(Integer,default=1,nullable=False)
 # 汇总口径：有效作业数 + 至多三件的组合计数（缺项表示未上报，不当零）
 valid_jobs=Column(Integer,nullable=False);combo_counts=Column(JSON,nullable=False)
 checksum=Column(String(64),nullable=False);supersedes_id=Column(Integer,nullable=True)
 note=Column(Text,default='');created=Column(String(40));activated=Column(String(40),nullable=True)
 # 仅生效行写入 scope_key，配合唯一索引保证每站每周期每设备至多一份生效汇总（修订替换而非累加）
 active_scope=Column(String(120),nullable=True)
 __table_args__=(UniqueConstraint('station_code','cycle','equipment','version',name='uq_summary_version'),
                 UniqueConstraint('active_scope',name='uq_summary_active_scope'),
                 Index('ix_summary_scope','station_code','cycle','equipment','state'))
class MiningRun(Base):
 __tablename__='mining_runs'
 id=Column(Integer,primary_key=True);name=Column(String(100));equipment=Column(String(40));min_support=Column(Float);min_confidence=Column(Float);min_lift=Column(Float);state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
 # 冻结的来源版本清单与合并快照，提交即固化，后续修订不改变已有报告
 source_manifest=Column(JSON,nullable=True);snapshot=Column(JSON,nullable=True)
class AssociationRule(Base):
 __tablename__='association_rules'
 id=Column(Integer,primary_key=True);run_id=Column(Integer,ForeignKey('mining_runs.id'));signature=Column(String(200));antecedent=Column(JSON);consequent=Column(JSON);support=Column(Float);confidence=Column(Float);lift=Column(Float);count=Column(Integer)
 __table_args__=(UniqueConstraint('run_id','signature'),)
class Kit(Base):
 __tablename__='kits'
 id=Column(Integer,primary_key=True);name=Column(String(100));rule_id=Column(Integer,ForeignKey('association_rules.id'));parts=Column(JSON);note=Column(Text);status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
