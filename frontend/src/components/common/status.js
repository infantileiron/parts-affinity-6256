import {esc} from '../../utils/html.js';import {SUMMARY_STATES} from '../../constants/enums.js';
export function badge(s){const label=SUMMARY_STATES[s]||s;return `<span class="tag ${s==='active'?'ok':s==='void'?'muted':''}">${esc(label)}</span>`}
