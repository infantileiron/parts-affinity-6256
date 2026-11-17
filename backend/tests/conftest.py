import os,json,sys,types
from pathlib import Path
import pytest
# 隔离环境：内存 SQLite + 假 Redis，测试代码与被测代码分离
os.environ.setdefault('JWT_SECRET','test-secret')
os.environ.setdefault('DATABASE_URL','sqlite:///:memory:')
os.environ.setdefault('REDIS_URL','redis://localhost:6379/0')
import tempfile
os.environ.setdefault('ARTIFACTS_DIR',tempfile.mkdtemp(prefix='artifacts-'))
class FakeRedis:
 def __init__(self,*a,**k):self.q=[]
 @classmethod
 def from_url(cls,*a,**k):return cls()
 def rpush(self,k,v):self.q.append(v);return len(self.q)
 def blpop(self,k,timeout=0):return None
 def ping(self):return True
redis_mod=types.ModuleType('redis')
redis_mod.Redis=FakeRedis
redis_mod.RedisError=Exception
sys.modules['redis']=redis_mod
from fastapi.testclient import TestClient
@pytest.fixture()
def client(monkeypatch):
 import src.config.database as db_mod
 from sqlalchemy import create_engine
 from sqlalchemy.orm import sessionmaker
 from sqlalchemy.pool import StaticPool
 # StaticPool + 单连接，保证应用线程、worker 与测试看到同一个内存库
 engine=create_engine('sqlite:///:memory:',connect_args={'check_same_thread':False},
  poolclass=StaticPool)
 TestSession=sessionmaker(bind=engine,expire_on_commit=False)
 monkeypatch.setattr(db_mod,'engine',engine)
 monkeypatch.setattr(db_mod,'Session',TestSession)
 import src.models.entities  # noqa: F401
 db_mod.Base.metadata.create_all(engine)
 # 共享内存库连接，保证多连接看到同一份数据
 @pytest.fixture()
 def _noop():pass
 from src.main import app
 from src.utils.security import hash_password
 from src.models.entities import User
 with TestSession() as s:
  for role in ('admin','analyst','viewer'):
   s.add(User(email=role+'@demo.local',role=role,password=hash_password('Demo123!')))
  s.commit()
 with TestClient(app) as c:
  yield c
def token(client,role='analyst'):
 r=client.post('/auth/login',json={'email':role+'@demo.local','password':'Demo123!'})
 assert r.status_code==200
 return {'Authorization':'Bearer '+r.json()['token']}
@pytest.fixture()
def auth(client):return lambda role='analyst':token(client,role)
