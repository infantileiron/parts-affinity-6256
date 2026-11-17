from pydantic import BaseModel,Field,field_validator,model_validator
from typing import Literal,Optional
from src.constants.enums import PARTS,EQUIPMENT,CYCLE_RE,STATION_CODE_RE,SUMMARY_MAX_COMBO
class Login(BaseModel):email:str;password:str
class JobInput(BaseModel):
 code:str=Field(min_length=1,max_length=60)
 equipment:Literal['泵组','压缩机','风机']
 parts:list[str]=Field(min_length=1,max_length=30)
 note:str=Field(default='',max_length=1000)
 # 本地补录的分站与周期：成对出现，用于明细口径的范围判断
 station_code:Optional[str]=Field(default=None,max_length=40)
 cycle:Optional[str]=Field(default=None,max_length=20)
 @field_validator('parts')
 @classmethod
 def validate_parts(cls,v):
  values=sorted(set(p.strip() for p in v if p.strip()))
  if not values:raise ValueError('用件集合不能为空')
  if any(p not in PARTS for p in values):raise ValueError('备件必须来自12项标准目录')
  return values
 @field_validator('station_code')
 @classmethod
 def validate_station(cls,v):
  if v is not None:
   v=v.strip()
   if not STATION_CODE_RE.match(v):raise ValueError('分站编码需为2-40位字母数字、下划线或中划线')
  return v
 @field_validator('cycle')
 @classmethod
 def validate_cycle(cls,v):
  if v is not None and not CYCLE_RE.match(v.strip()):raise ValueError('周期格式应为 YYYY-MM 或 YYYY-Www')
  return v.strip() if v else v
 @model_validator(mode='after')
 def scope_pair(self):
  if bool(self.station_code)!=bool(self.cycle):raise ValueError('分站与周期必须同时填写或同时留空')
  return self
class RunInput(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 equipment:Literal['全部','泵组','压缩机','风机']='全部'
 min_support:float=Field(default=.15,gt=0,le=1,allow_inf_nan=False)
 min_confidence:float=Field(default=.6,gt=0,le=1,allow_inf_nan=False)
 min_lift:float=Field(default=1,ge=0,le=50,allow_inf_nan=False)
 # 挖掘来源：仅本地明细 / 仅生效汇总 / 联用（默认）
 source:Literal['local','summary','combined']='combined'
 station_codes:Optional[list[str]]=None
 cycles:Optional[list[str]]=None
 @field_validator('station_codes')
 @classmethod
 def station_list(cls,v):
  if v is None:return v
  v=[x.strip() for x in v if x and x.strip()]
  if any(not STATION_CODE_RE.match(x) for x in v):raise ValueError('分站编码格式不正确')
  return sorted(set(v))
 @field_validator('cycles')
 @classmethod
 def cycle_list(cls,v):
  if v is None:return v
  v=[x.strip() for x in v if x and x.strip()]
  if any(not CYCLE_RE.match(x) for x in v):raise ValueError('周期格式应为 YYYY-MM 或 YYYY-Www')
  return sorted(set(v))
class KitInput(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 rule_id:int=Field(gt=0)
 note:str=Field(min_length=8,max_length=2000)
class KitEdit(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 note:str=Field(min_length=8,max_length=2000)
class RuleOutput(BaseModel):
 id:int;run_id:int;antecedent:list[str];consequent:list[str];support:float;confidence:float;lift:float;count:int
