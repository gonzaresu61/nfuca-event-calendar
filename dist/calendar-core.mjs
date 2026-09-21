export function tokyoToday(now = new Date()) {
  return new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
}
export function parseDay(day) { return new Date(`${day}T12:00:00+09:00`); }
export function nextDay(day) { return new Date(Date.parse(`${day}T00:00:00Z`) + 86400000).toISOString().slice(0,10); }
export function expandEntries(events, today) {
  return events.flatMap(e => {
    const entries=[];
    for(let d=e.startDate; d<=e.endDate; d=nextDay(d)) {
      entries.push({...e,date:d,kind:'event'});
    }
    if(e.deadline) entries.push({...e,date:e.deadline,kind:'deadline'});
    return entries;
  }).sort((a,b)=>a.date.localeCompare(b.date)||a.kind.localeCompare(b.kind)||a.title.localeCompare(b.title,'ja'));
}
export function monthDays(year, month) {
  const first=new Date(Date.UTC(year,month,1));
  const count=new Date(Date.UTC(year,month+1,0)).getUTCDate();
  const size=Math.ceil((first.getUTCDay()+count)/7)*7;
  return Array.from({length:size},(_,i)=>new Date(Date.UTC(year,month,1-first.getUTCDay()+i)).toISOString().slice(0,10));
}
