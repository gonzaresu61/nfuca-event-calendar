import test from 'node:test';
import assert from 'node:assert/strict';
import {tokyoToday,expandEntries,monthDays} from '../dist/calendar-core.mjs';
test('date boundary follows Japan even on a UTC computer',()=>{
 assert.equal(tokyoToday(new Date('2026-09-19T15:01:00Z')),'2026-09-20');
});
test('multi-day event appears on every day; expired deadlines are hidden',()=>{
 const events=[{title:'ツアー',startDate:'2026-10-10',endDate:'2026-10-11',deadline:'2026-09-07'}];
 assert.deepEqual(expandEntries(events,'2026-09-20').map(e=>e.date),['2026-10-10','2026-10-11']);
 assert.deepEqual(expandEntries(events,'2026-10-11').map(e=>e.date),['2026-10-11']);
 assert.deepEqual(expandEntries(events,'2026-10-12'),[]);
});
test('deadline and event on the same date stay distinct',()=>{
 const entries=expandEntries([{title:'会',startDate:'2026-09-20',endDate:'2026-09-20',deadline:'2026-09-20'}],'2026-09-20');
 assert.equal(entries.length,2);assert.equal(new Set(entries.map(e=>e.kind)).size,2);
});
test('Sunday grid handles leap year and year boundary',()=>{
 const leap=monthDays(2028,1);assert.ok(leap.includes('2028-02-29'));assert.equal(leap.length%7,0);
 const january=monthDays(2027,0);assert.equal(january[0],'2026-12-27');
 assert.equal(new Set(january).size,january.length);
});
