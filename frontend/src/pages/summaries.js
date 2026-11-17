import {state} from '../stores/session.js';import {esc} from '../utils/html.js';import {badge} from '../components/common/status.js';import {field,select} from '../components/common/fields.js';import {post} from '../api/client.js';import {EQUIPMENT,PARTS} from '../constants/enums.js';
function comboRows(){
 // 组合录入区：最多三行，每行备件（逗号分隔，至多三件）与计数
 return [1,2,3].map(i=>`<div class="combo-row"><input name="combo_parts_${i}" placeholder="组合备件，逗号分隔（至多3件）" maxlength="60"><input name="combo_count_${i}" type="number" min="1" placeholder="计数" style="width:90px"></div>`).join('')
}
export function render(){return `<div class="split"><section class="panel"><h2>分站汇总 / ${state.summaries.length} 份</h2>
<p>分站仅提供按设备、周期汇总的有效作业数与至多三件的组合计数。待核对单据不参与挖掘；生效后每站同周期同设备仅保留一份，修订以新版本替换。</p>
<div class="scroll"><table><thead><tr><th>分站</th><th>周期</th><th>设备</th><th>版本</th><th>状态</th><th>有效作业</th><th>组合数</th><th>操作</th></tr></thead><tbody>
${state.summaries.map(r=>`<tr><td>${esc(r.station_code)}</td><td>${esc(r.cycle)}</td><td>${esc(r.equipment)}</td><td>v${r.version}${r.supersedes_id?` ← #${r.supersedes_id}`:''}</td><td>${badge(r.state)}</td><td>${r.valid_jobs}</td><td>${r.combo_counts.length}</td><td>${r.state==='pending'?`<button data-activate="${r.id}">核对生效</button>`:`<button data-detail="${r.id}">查看计数</button>`}</td></tr>`).join('')||'<tr><td colspan="8">暂无汇总。右侧导入或粘贴分站上报数据。</td></tr>'}</tbody></table></div>
<div id="combo-detail" class="notice"></div>
</section><aside class="side"><h2>导入分站汇总</h2><form id="summary">
${field('分站编码','station_code','text','required placeholder="ST-NORTH"')}
${field('周期（YYYY-MM 或 YYYY-Www）','cycle','text','required placeholder="2026-W46"')}
${select('设备类型','equipment',EQUIPMENT.map(t=>[t,t]))}
${field('有效作业数','valid_jobs','number','min=1 required')}
<label>组合计数（至多三件，缺项留空即可，不会当零）</label>${comboRows()}
<label>备注<textarea name="note" rows="2"></textarea></label>
<button class="primary">导入待核对</button><p class="notice" id="summary-feedback"></p>
</form><details><summary>12项标准备件目录</summary><p>${PARTS.join('、')}</p></details></aside></div>`}
export function bind(run,refresh){
 document.querySelectorAll('[data-activate]').forEach(b=>b.onclick=()=>run(async()=>{
  await post('/summaries/'+b.dataset.activate+'/activate',{});
  await refresh();
 }));
 document.querySelectorAll('[data-detail]').forEach(b=>b.onclick=()=>{
  const r=state.summaries.find(x=>String(x.id)===b.dataset.detail);
  document.querySelector('#combo-detail').innerHTML=r.combo_counts.map(c=>`${esc(c.parts.join('+'))}：<strong>${c.count}</strong>`).join(' ｜ ')||'无组合计数';
 });
}
export function payload(form){
 const v=Object.fromEntries(new FormData(form));
 const combos=[];
 for(let i=1;i<=3;i++){
  const parts=(v['combo_parts_'+i]||'').split(/[,，]/).map(x=>x.trim()).filter(Boolean);
  const count=Number(v['combo_count_'+i]);
  if(parts.length&&count)combos.push({parts,count});
 }
 return {station_code:v.station_code,cycle:v.cycle,equipment:v.equipment,valid_jobs:Number(v.valid_jobs),combos,note:v.note||''};
}
