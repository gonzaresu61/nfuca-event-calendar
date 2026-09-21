import {tokyoToday,expandEntries,monthDays} from './calendar-core.mjs';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl=s=>{try{const u=new URL(s);return u.protocol==='https:'?esc(u.href):'#';}catch{return '#';}};
let today=tokyoToday(), selected=today, year=Number(today.slice(0,4)),month=Number(today.slice(5,7))-1, category='all',mode='month',data={events:[],unconfirmed:[]};
const dayLabel=(d,weekday=false)=>new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',month:'long',day:'numeric',...(weekday?{weekday:'short'}:{})}).format(new Date(d+'T12:00:00+09:00'));
const filtered=()=>data.events.filter(e=>category==='all'||e.category===category);
const entries=()=>expandEntries(filtered(),today);
const dateRange=e=>e.startDate===e.endDate?dayLabel(e.startDate,true):`${dayLabel(e.startDate)}〜${dayLabel(e.endDate,true)}`;
const deadlineText=e=>e.deadline?`${dayLabel(e.deadline,true)}${e.deadlineTime?' '+e.deadlineTime:''}${e.deadline<today?'（締切済み）':''}`:'記載なし・原文をご確認ください';
function eventDetail(e){
  return `<article class="event-detail"><span class="pill ${e.kind==='deadline'?'deadline':''}">${e.kind==='deadline'?'申込締切':'開催日'}</span><h3>${esc(e.title)}</h3><p class="meta">${esc(e.category)}</p><p class="meta">開催：${esc(dateRange(e))}<br>${esc(e.time||'時間は原文をご確認ください')}</p><p class="meta">${esc(e.venue||'会場・形式は原文をご確認ください')}</p><p class="deadline-line ${e.deadline&&e.deadline<today?'closed':''}">申込締切：${esc(deadlineText(e))}</p><a class="detail-link" href="${safeUrl(e.sourceUrl)}" target="_blank" rel="noopener noreferrer">公式の案内を見る ↗</a>${e.deadlineSourceUrl&&e.deadlineSourceUrl!==e.sourceUrl?`<br><a class="detail-link" href="${safeUrl(e.deadlineSourceUrl)}" target="_blank" rel="noopener noreferrer">締切の記載元 ↗</a>`:''}</article>`;
}
function render(){
  const all=entries(), prefix=`${year}-${String(month+1).padStart(2,'0')}`, inMonth=all.filter(e=>e.date.startsWith(prefix));
  $('month-label').textContent=`${year}年 ${month+1}月`;
  $('month-count').textContent=`開催 ${inMonth.filter(e=>e.kind==='event').length}件・締切 ${inMonth.filter(e=>e.kind==='deadline').length}件`;
  $('month-content').hidden=mode!=='month'; $('list-content').hidden=mode!=='list';
  $('month-view').setAttribute('aria-pressed',mode==='month'); $('list-view').setAttribute('aria-pressed',mode==='list');
  $('calendar').innerHTML=monthDays(year,month).map(d=>{
    const events=all.filter(e=>e.date===d), outside=!d.startsWith(prefix);
    return `<button type="button" class="day ${outside?'outside':''} ${d===selected?'selected':''} ${d===today?'is-today':''}" data-date="${d}" aria-pressed="${d===selected}" aria-label="${esc(d+' '+events.map(e=>(e.kind==='deadline'?'申込締切 ':'開催 ')+e.title).join('、'))}"><span class="day-number">${Number(d.slice(8))}</span>${events.slice(0,2).map(e=>`<span class="chip ${e.kind==='deadline'?'deadline':''}"><span class="chip-label">${e.kind==='deadline'?'締切':'開催'}</span>${esc(e.title)}</span>`).join('')}${events.length>2?`<span class="more">＋${events.length-2}件</span>`:''}</button>`;
  }).join('');
  $('calendar').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.date;if(!selected.startsWith(prefix)){year=Number(selected.slice(0,4));month=Number(selected.slice(5,7))-1;}render();}));
  $('detail-heading').textContent=dayLabel(selected,true);
  const chosen=all.filter(e=>e.date===selected);
  $('details').innerHTML=chosen.length?chosen.map(eventDetail).join(''):`<div class="empty"><div class="empty-mark" aria-hidden="true">▦</div>${selected<today?'終了した予定は表示していません。':'この日の予定はありません。'}<br>カレンダーの日付を選んでください。</div>`;
  $('list-content').innerHTML=inMonth.length?inMonth.map(e=>`<div class="list-row"><div class="list-date">${dayLabel(e.date,true)}</div>${eventDetail(e)}</div>`).join(''):'<p class="empty">この月の予定はありません。</p>';
  const upcoming=filtered().filter(e=>e.endDate>=today).sort((a,b)=>a.startDate.localeCompare(b.startDate));
  $('upcoming-count').textContent=`${upcoming.length}件`;
  $('upcoming').innerHTML=upcoming.length?upcoming.map(e=>`<article class="upcoming-card"><div class="date-block">${Number(e.startDate.slice(5,7))}月<strong>${Number(e.startDate.slice(8))}</strong>${e.endDate!==e.startDate?'〜'+dayLabel(e.endDate):new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',weekday:'short'}).format(new Date(e.startDate+'T12:00:00+09:00'))}</div><div><span class="category-label">${esc(e.category)}</span><h3><a href="${safeUrl(e.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(e.title)} ↗</a></h3><p class="meta">${esc(e.time||'時間は原文で確認')}</p><p class="meta">${esc(e.venue||'会場・形式は原文で確認')}</p><p class="deadline-line ${e.deadline&&e.deadline<today?'closed':''}">締切：${esc(deadlineText(e))}</p></div></article>`).join(''):'<p class="empty">現在掲載されている開催予定はありません。</p>';
  const unknown=(data.unconfirmed||[]).filter(e=>category==='all'||e.category===category);
  $('unconfirmed-section').hidden=!unknown.length;
  $('unconfirmed').innerHTML=unknown.map(e=>`<div class="unknown-item"><a href="${safeUrl(e.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(e.title)} ↗</a><br><span class="meta">${esc(e.reason)}</span></div>`).join('');
}
function moveMonth(n){const d=new Date(Date.UTC(year,month+n,1));year=d.getUTCFullYear();month=d.getUTCMonth();selected=`${year}-${String(month+1).padStart(2,'0')}-01`;render();}
$('prev').onclick=()=>moveMonth(-1);$('next').onclick=()=>moveMonth(1);$('today').onclick=()=>{today=tokyoToday();year=Number(today.slice(0,4));month=Number(today.slice(5,7))-1;selected=today;render();};
$('category').onchange=e=>{category=e.target.value;render();};$('month-view').onclick=()=>{mode='month';render();};$('list-view').onclick=()=>{mode='list';render();};
function showNotice(text){$('notice').hidden=false;$('notice').textContent=text;}
render();
async function load(){try{
  const response=await fetch('./data/events.json',{cache:'no-cache'});if(!response.ok)throw new Error('fetch failed');
  const result=await response.json();if(!Array.isArray(result.events)||!result.generatedAt)throw new Error('invalid data');data=result;
  const stamp=new Date(data.generatedAt);$('updated').textContent='最終確認：'+new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}).format(stamp);
  if(Date.now()-stamp.getTime()>8*86400000)showNotice('最終確認から8日以上経過しています。最新の日程と締切は公式の案内をご確認ください。');
  else if(data.warnings?.length)showNotice('一部の案内は再確認が必要です。日付確認要の欄と公式の案内をご確認ください。');
  render();
}catch{$('updated').textContent='情報を読み込めませんでした';showNotice('カレンダーの情報を取得できませんでした。ページを再読み込みするか、公式のお知らせをご確認ください。');}}
load();
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&tokyoToday()!==today){today=tokyoToday();render();}});
