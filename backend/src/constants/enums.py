ROLES=('admin','analyst','viewer')
STATES=('queued','running','done','failed')
EQUIPMENT=('泵组','压缩机','风机')
PARTS=('轴承', '密封圈', '润滑脂', '滤芯', '垫片', '联轴器', '皮带', '紧固件', '叶轮', '阀片', '传感器', '清洗剂')
# 分站汇总状态：待核对 → 生效（或作废）；生效后只能由同站同周期修订替换
SUMMARY_STATES=('pending','active','void')
SUMMARY_MAX_COMBO=3
# 周期形如 2026-W46（ISO周）或 2026-11（月），分站编码字母数字与中划线
import re
CYCLE_RE=re.compile(r'^\d{4}-(W(0[1-9]|[1-4]\d|5[0-3])|(0[1-9]|1[0-2]))$')
STATION_CODE_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{1,39}$')
