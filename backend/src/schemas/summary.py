from pydantic import BaseModel,Field,field_validator
from typing import Literal
from src.constants.enums import PARTS,EQUIPMENT,CYCLE_RE,STATION_CODE_RE,SUMMARY_MAX_COMBO
class StationInput(BaseModel):
 code:str=Field(min_length=2,max_length=40)
 name:str=Field(min_length=2,max_length=100)
 @field_validator('code')
 @classmethod
 def code_ok(cls,v):
  v=v.strip()
  if not STATION_CODE_RE.match(v):raise ValueError('分站编码需为2-40位字母数字、下划线或中划线')
  return v
 @field_validator('name')
 @classmethod
 def name_ok(cls,v):return v.strip()
class Combo(BaseModel):
 # 至多三件的组合计数；组合去重、非空，计数为正整数
 parts:list[str]=Field(min_length=1,max_length=SUMMARY_MAX_COMBO)
 count:int=Field(gt=0)
 @field_validator('parts')
 @classmethod
 def parts_ok(cls,v):
  v=sorted(set(p.strip() for p in v if p.strip()))
  if not v:raise ValueError('组合不能为空')
  if len(v)>SUMMARY_MAX_COMBO:raise ValueError('分站汇总至多提供三件组合')
  if any(p not in PARTS for p in v):raise ValueError('备件必须来自12项标准目录')
  return v
class SummaryInput(BaseModel):
 station_code:str=Field(min_length=2,max_length=40)
 cycle:str=Field(max_length=20)
 equipment:Literal['泵组','压缩机','风机']
 valid_jobs:int=Field(gt=0)
 combos:list[Combo]=Field(min_length=1)
 note:str=Field(default='',max_length=1000)
 @field_validator('station_code')
 @classmethod
 def station_ok(cls,v):
  v=v.strip()
  if not STATION_CODE_RE.match(v):raise ValueError('分站编码格式不正确')
  return v
 @field_validator('cycle')
 @classmethod
 def cycle_ok(cls,v):
  v=v.strip()
  if not CYCLE_RE.match(v):raise ValueError('周期格式应为 YYYY-MM 或 YYYY-Www')
  return v
 @field_validator('combos')
 @classmethod
 def combo_consistency(cls,v):
  seen=set()
  for c in v:
   key=tuple(c.parts)
   if key in seen:raise ValueError('存在重复组合：'+'、'.join(c.parts))
   seen.add(key)
  return v
