import {api,post} from './api/client.js';import {state} from './stores/session.js';import {routes,page} from './router/index.js';import {values,feedback} from './hooks/form.js';import {esc} from './utils/html.js';import * as jobs from './pages/jobs.js';import * as summaries from './pages/summaries.js';import * as mining from './pages/mining.js';import * as rules from './pages/rules.js';import * as kits from './pages/kits.js';
const pages=[jobs,summaries,mining,rules,kits];
const root=document.querySelector('#app');
async function load(){[state.jobs,state.runs,state.kits,state.stations,state.summaries]=await Promise.all(['/jobs','/runs','/kits','/stations','/summaries'].map(x=>api(x)));state.selected=state.runs.find(r=>r.id===state.selected?.id)||state.runs[0]||null;state.rules=state.selected?await api('/rules?run_id='+state.selected.id):[];state.reconciliation=null}
function login(){root.innerHTML=`<div class="login"><section class="cover"><div class="eyebrow">YUAN HANG / MAINTENANCE CHART 008</div><h1>把一起更换的备件，<br>放回作业背景。</h1><p>远航设备服务 · 维修策划航图<br>作业集合 → 分站汇总 → Apriori规则 → 兼容性核对 → 备件包签核<br>180张作业 / 12项备件 / 3种设备 / 分站周期汇总</p></section><section><div class="eyebrow">PARTS AFFINITY</div><h2>登录维修航图</h2><form id="login"><label>工作邮箱<input name="email" type="email" value="analyst@demo.local" required></label><label>密码<input name="password" type="password" value="Demo123!" required></label><button class="primary">进入联用发现</button></form><p id="error" class="error"></p><p>admin / analyst / viewer @demo.local<br>密码：Demo123!</p></section></div>`;document.querySelector('form').onsubmit=e=>{e.preventDefault();run(async()=>{let d=await post('/auth/login',values(e.target));localStorage.setItem('token',d.token);state.user=d.user;await load();render()})}}
function render(){let n=Math.min(4,Math.max(0,page()));root.innerHTML=`<header><div class="brand">远航 / 维保联用航图 <span class="eyebrow">PARTS AFFINITY</span></div><div>${esc(state.user.email)} · ${esc(state.user.role)} <button id="logout">退出</button></div></header><div class="layout"><nav>${routes.map((r,i)=>`<button data-nav="${i}" class="${i===n?'active':''}">0${i+1} ${r}</button>`).join('')}<span class="eyebrow">SERVICE ENGINEERING / 2026</span></nav><main><div class="intro"><div><div class="eyebrow">MAINTENANCE ROUTE / 0${n+1}</div><h1>${routes[n]}</h1><p>本地明细与生效分站汇总加权联用。缺项不当零，矛盾计数拒收，同范围不混算，每批冻结完整来源版本。</p></div><span class="tag">泵组 / 压缩机 / 风机</span></div><p id="error" class="error"></p>${pages[n].render()}</main></div>`;bind(n);if(state.user.role==='viewer')document.querySelectorAll('form button,[data-kit-rule],[data-activate]').forEach(b=>{b.disabled=true;b.textContent='观察员只读'});if(state.chosenRule&&n===4){let x=document.querySelector('[name=rule_id]');if(x)x.value=state.chosenRule}}
async function run(fn){try{await fn()}catch(e){feedback(e.message)}}
function bind(n){
 document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>location.hash=b.dataset.nav);
 document.querySelector('#logout').onclick=()=>{localStorage.removeItem('token');state.user=null;login()};
 for(let [id,path] of [['job','/jobs'],['mining','/runs'],['kit','/kits']]){const f=document.querySelector('#'+id);if(f)f.onsubmit=e=>{e.preventDefault();run(async()=>{
  let d=values(f);
  for(let k of ['rule_id','min_support','min_confidence','min_lift'])if(k in d)d[k]=Number(d[k]);
  if(id==='job'){
   d.parts=d.parts.split(/[,，]/).map(v=>v.trim()).filter(Boolean);
   d.station_code=d.station_code?.trim()||null;d.cycle=d.cycle?.trim()||null;
  }
  if(id==='mining'){
   d.station_codes=d.station_codes?d.station_codes.split(/[,，]/).map(v=>v.trim()).filter(Boolean):null;
   d.cycles=d.cycle_list?d.cycle_list.split(/[,，]/).map(v=>v.trim()).filter(Boolean):null;delete d.cycle_list;
  }
  let record=d.record_id;delete d.record_id;
  let created=record?await api(path+'/'+record,{method:'PUT',body:JSON.stringify(d)}):await post(path,d);
  if(id==='mining')state.selected=created;
  await load();render();
 })}}
 const sf=document.querySelector('#summary');if(sf)sf.onsubmit=e=>{e.preventDefault();run(async()=>{
  const payload=summaries.payload(sf);
  if(!payload.combos.length)throw Error('至少填写一个组合计数');
  await post('/summaries/import',payload);await load();render();
 })};
 if(pages[n].bind)pages[n].bind(run,async()=>{await load();render()});
 document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>run(async()=>{state.selected=await api('/runs/'+b.dataset.run);await load();render()}));
 document.querySelectorAll('[data-recon]').forEach(b=>b.onclick=()=>run(async()=>{
  const rec=await api('/runs/'+b.dataset.recon+'/reconciliation');state.reconciliation=rec;
  document.querySelector('#recon').innerHTML=`<div class="scroll"><table><thead><tr><th>分站</th><th>本地事务</th><th>汇总有效作业</th><th>来源版本</th></tr></thead><tbody>${rec.stations.map(x=>`<tr><td>${esc(x.station_code)}</td><td>${x.local_transactions}</td><td>${x.summary_jobs}</td><td>${esc(x.reports.map(r=>`#${r.report_id} v${r.version} ${r.cycle}`).join('；')||'—')}</td></tr>`).join('')}</tbody></table></div><p class="notice">合计有效作业 ${rec.total_valid_jobs}，来源 ${esc(rec.source)}</p>`;
 }));
 document.querySelectorAll('[data-kit-rule]').forEach(b=>b.onclick=()=>{state.chosenRule=b.dataset.kitRule;location.hash='4'});
 document.querySelectorAll('[data-approve]').forEach(b=>b.onclick=()=>run(async()=>{await post('/kits/'+b.dataset.approve+'/approve',{});await load();render()}));
 const refresh=document.querySelector('#refresh');if(refresh)refresh.onclick=()=>run(async()=>{await load();render()});
 const download=document.querySelector('#download');if(download)download.onclick=()=>run(async()=>{let d=await api('/runs/'+state.selected.id+'/export');let u=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=u;a.download='parts-affinity-'+d.id+'.json';a.click();URL.revokeObjectURL(u)});
}
window.onhashchange=()=>{if(state.user){render();window.scrollTo(0,0)}};if(localStorage.getItem('token'))run(async()=>{try{state.user=await api('/me');await load();render()}catch(e){localStorage.removeItem('token');login();feedback(e.message)}});else login();
