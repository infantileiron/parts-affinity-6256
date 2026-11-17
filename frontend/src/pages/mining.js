import {state} from '../stores/session.js';import {esc} from '../utils/html.js';import {badge} from '../components/common/status.js';import {field,select} from '../components/common/fields.js';import {EQUIPMENT,SOURCES} from '../constants/enums.js';
function selectedPanel(r){
 if(!r)return '<p class="notice">配置阈值后提交后台挖掘。先从支持度0.15、置信度0.6开始，再结合业务解释规则。</p>';
 const source=(r.source_manifest&&r.source_manifest.source)||'combined';
 const head=`<h3>${esc(r.name)}</h3><p>设备 ${esc(r.equipment)} · 来源 ${esc(source)} · support≥${r.min_support} · confidence≥${r.min_confidence} · lift≥${r.min_lift}</p>`;
 const body=r.state==='done'
  ?`<div class="metrics"><div><strong>${r.result.valid_jobs}</strong>有效作业</div><div><strong>${r.result.frequent.length}</strong>频繁项集</div><div><strong>${r.result.rules.length}</strong>关联规则</div></div><p class="notice">${esc(r.result.method)}</p><button data-nav="3">进入规则解释 →</button>`
  :`<p class="notice">${esc(r.error||'任务已入队，请刷新查看后台计算。')}</p>`;
 const recon=`<h3>逐站对账</h3><div id="recon"><button data-recon="${r.id}">加载对账</button></div>`;
 return head+body+recon;
}
export function render(){
 const r=state.selected;
 const versions=state.runs.map(v=>`<button class="study" data-run="${v.id}">#${v.id} ${esc(v.name)} · ${esc(v.state)}</button>`).join('');
 return `<div class="split"><section class="panel"><h2>规则挖掘航线 ${r?badge(r.state):''}</h2>${selectedPanel(r)}<h3>挖掘版本</h3>${versions}</section><aside class="side"><h2>设定阈值与来源</h2><form id="mining">${field('批次名称','name','text','required value="11月维保联用复核"')}${select('设备类型','equipment',['全部',...EQUIPMENT].map(t=>[t,t]))}${select('挖掘来源','source',SOURCES)}<label>限定分站（可留空，逗号分隔多个编码）<input name="station_codes" placeholder="ST-NORTH,ST-SOUTH"></label><label>限定周期（可留空，逗号分隔）<input name="cycle_list" placeholder="2026-W45,2026-W46"></label>${field('最小支持度','min_support','number','min=0.01 max=1 step=0.01 value=0.15 required')}${field('最小置信度','min_confidence','number','min=0.01 max=1 step=0.01 value=0.6 required')}${field('最小提升度','min_lift','number','min=0 max=50 step=0.1 value=1 required')}<p>提交即冻结完整来源版本：仅读取生效汇总，待核对不参与；明细与汇总同站同周期重叠将拒绝混算。缺项不当零。</p><button class="primary">提交后台挖掘</button></form><p><button id="refresh">刷新计算状态</button></p></aside></div>`;
}
