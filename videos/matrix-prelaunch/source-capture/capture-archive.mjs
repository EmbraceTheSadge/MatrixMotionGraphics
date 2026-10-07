// Captures the real Archive interaction (real clicks) at 2x into assets/archive/. Usage: npm i playwright && node capture-archive.mjs ../assets/archive
import { chromium } from 'playwright';
import fs from 'fs';
const OUT = process.argv[2];
const b = await chromium.launch({ proxy: { server: process.env.HTTPS_PROXY } });
const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
const log = { captured_at: new Date().toISOString(), viewport: '1920x1080 @2x', method: 'Playwright/Chromium, real clicks on the live site', steps: [] };
const box = async (loc) => { const r = await loc.boundingBox(); return r && { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; };
const shot = async (name, loc, label) => {
  let click = null;
  if (loc) { click = await box(loc); await loc.hover(); }
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${OUT}/${name}.png` });
  log.steps.push({ name, url: p.url(), click, clickLabel: label || null, scrollY: await p.evaluate(()=>window.scrollY) });
  console.log(name, p.url(), JSON.stringify(click));
};
await p.goto('https://strategies.matrix.finance/', { waitUntil: 'networkidle', timeout: 60000 }); await p.waitForTimeout(1500);
let t = p.getByText('ENTER THE ARCHIVE').first(); await shot('arc-1-home', t, 'ENTER THE ARCHIVE');
await t.click(); await p.waitForLoadState('networkidle');
t = p.getByText('Sideways', { exact: true }).first(); await shot('arc-2-market', t, 'Sideways');
await t.click(); await p.waitForLoadState('networkidle');
t = p.getByText('High-Volatility Chop').first(); await shot('arc-3-phase', t, 'High-Volatility Chop');
await t.click(); await p.waitForLoadState('networkidle');
t = p.getByText('CONTINUE', { exact: true }).first(); await shot('arc-4-assets', t, 'CONTINUE');
await t.click(); await p.waitForLoadState('networkidle');
t = p.getByText(/^Capital Preservation$/i).first(); await shot('arc-5-objective', t, 'Capital Preservation');
await t.click(); await p.waitForLoadState('networkidle');
t = p.getByText('OPEN RECORD', { exact: true }).first(); await shot('arc-6-results', t, 'OPEN RECORD');
await t.click(); await p.waitForLoadState('networkidle'); await p.waitForTimeout(6000);
await p.mouse.move(1900, 1070);
await shot('arc-7-record-top');
await p.evaluate(()=>{ const h=[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.trim()==='Risk'); h.scrollIntoView({block:'start'}); window.scrollBy(0,-110); });
await shot('arc-8-record-risk');
// risk panel geometry (CSS px in the viewport) for the close-up
const g = await p.evaluate(()=>{ const h=[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.trim()==='Risk'); const sec=h.closest('section')||h.parentElement.parentElement; const r=sec.getBoundingClientRect(); const hr=h.getBoundingClientRect(); return {section:{x:r.x,y:r.y,w:r.width,h:r.height}, heading:{x:hr.x,y:hr.y}}; });
log.riskGeometry = g;
fs.writeFileSync(`${OUT}/archive-capture-log.json`, JSON.stringify(log, null, 1));
await b.close();
