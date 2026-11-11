/* Browser QA for generated readers. Pass environment-discovered Playwright/browser paths. */
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const argv=process.argv.slice(2),input=argv[0];
function option(name){const i=argv.indexOf(name);return i>=0?argv[i+1]:undefined}
function ensure(condition,message){if(!condition)throw Error(message)}
(async()=>{
 ensure(input,'Usage: node check_reader.cjs FILE.html [--playwright PACKAGE] [--browser EXE] [--screenshots DIRECTORY]');
 const {chromium}=require(option('--playwright')||'playwright');
 const executablePath=option('--browser');
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),args:['--disable-gpu','--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const remote=[];page.on('request',request=>{if(/^https?:/.test(request.url()))remote.push(request.url())});
  await page.goto(pathToFileURL(path.resolve(input)).href,{waitUntil:'load'});
  await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});await page.evaluate(()=>document.fonts.ready);
  const shots=option('--screenshots');if(shots)fs.mkdirSync(shots,{recursive:true});
  async function shot(name){if(shots){await page.waitForTimeout(200);await page.screenshot({path:path.join(shots,name+'.png')})}}
  async function go(id){await page.evaluate(id=>{const el=document.getElementById(id);scrollTo({top:scrollY+el.getBoundingClientRect().top-document.querySelector('.section-nav').offsetHeight-22,behavior:'instant'})},id);await page.waitForTimeout(250)}
  const report=await page.evaluate(()=>{
   const pairs=[...document.querySelectorAll('.pair')],ids=[...document.querySelectorAll('[id]')].map(x=>x.id);
   const ordered=pairs.map(x=>Number(x.dataset.orderPage));
   const enMarks=[...document.querySelectorAll('.original mark')],zhMarks=[...document.querySelectorAll('.translation mark')];
   const aligned=enMarks.every(mark=>{const target=zhMarks.filter(m=>m.dataset.alignment===mark.dataset.alignment);return mark.dataset.alignment&&target.length>0&&target.every(m=>m.className===mark.className)})&&zhMarks.every(mark=>enMarks.some(m=>m.dataset.alignment===mark.dataset.alignment));
   return {pairs:pairs.length,translations:pairs.filter(x=>x.querySelector('.translation')).length,annotations:pairs.filter(x=>x.querySelector('.annotation[lang="zh-CN"]')).length,chineseAnnotations:pairs.every(x=>[...x.querySelectorAll('.annotation dd')].every(dd=>/[\u3400-\u9fff]/.test(dd.textContent))),englishHighlights:enMarks.length,chineseHighlights:zhMarks.length,alignedBilingualHighlights:aligned,uniqueIds:new Set(ids).size===ids.length,brokenAnchors:[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.getElementById(a.hash.slice(1))).map(a=>a.hash),orderedSourcePages:ordered.every((n,i)=>i===0||n>=ordered[i-1]),figures:document.querySelectorAll('.figure-panel').length,fontLora:document.fonts.check('17px Lora'),fontPlex:document.fonts.check('14px "IBM Plex Sans"'),desktopOverflow:document.documentElement.scrollWidth>innerWidth};
  });
  ensure(report.pairs>0&&report.pairs===report.translations&&report.pairs===report.annotations,'Unpaired source/translation/annotation');
  ensure(report.chineseAnnotations&&report.uniqueIds&&!report.brokenAnchors.length&&report.orderedSourcePages&&report.alignedBilingualHighlights,'Chinese annotation, bilingual alignment, anchor, or source-order invariant failed');
  ensure(report.fontLora&&report.fontPlex&&!report.desktopOverflow,'Font or desktop layout failed');
  await shot('desktop-top');
  const first=await page.locator('.pair').first().getAttribute('id');await go(first);await shot('desktop-paragraph');
  await go('argument');
  report.stickyDesktop=await page.locator('.legend').evaluate(el=>{const r=el.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&getComputedStyle(el.closest('.section-nav')).position==='sticky'});
  ensure(report.stickyDesktop,'Legend does not remain visible at the end');await shot('desktop-overview');
  await page.locator('[data-category="thesis"]').click();ensure(await page.evaluate(()=>document.body.classList.contains('off-thesis')&&[...document.querySelectorAll('.original mark.thesis,.translation mark.thesis')].every(m=>getComputedStyle(m).backgroundColor==='rgba(0, 0, 0, 0)')),'Synchronized bilingual highlight toggle failed');await page.locator('[data-category="thesis"]').click();
  await page.locator('#show-cn').uncheck();ensure(await page.locator('.pair .translation').first().isHidden(),'Translation toggle failed');await page.locator('#show-cn').check();
  await page.locator('#show-notes').uncheck();ensure(await page.locator('.pair .annotation').first().isHidden(),'Annotation toggle failed');await page.locator('#show-notes').check();
  await page.locator('#search').fill(first);await page.waitForTimeout(250);await page.locator('#search-next').click();ensure((await page.locator('#search-count').innerText()).startsWith('1 /'),'Search failed');await page.locator('#search').fill('');await page.waitForTimeout(250);
  await page.locator('.pair [data-page]').first().click();ensure(await page.locator('#source-dialog').evaluate(el=>el.open),'Source dialog failed');await page.locator('#dialog-close').click();
  if(report.figures){await page.locator('[data-figure]').first().click();await page.locator('#dialog-image').evaluate(img=>img.decode());ensure(await page.locator('#dialog-image').evaluate(img=>img.naturalWidth>0),'Figure decode failed');await shot('figure-modal');await page.keyboard.press('Escape');}
  for(const width of [390,320]){
   await page.setViewportSize({width,height:844});await go('argument');
   const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,legend:[...document.querySelectorAll('[data-category]')].map(el=>{const r=el.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,visible:r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth}}),display:getComputedStyle(document.querySelector('.pair')).display}));
   ensure(!metrics.overflow&&metrics.legend.length===5&&metrics.legend.every(x=>x.visible)&&metrics.display==='block',`Mobile ${width}: overflow, legend visibility, or single-column failure`);report['mobile'+width]=metrics;
   if(width===390){await shot('mobile-legend-overview');await go(first);await shot('mobile-paragraph');}
  }
  await page.setViewportSize({width:1440,height:1100});
  await page.evaluate(()=>{document.querySelectorAll('.figure-panel img').forEach(img=>{img.loading='eager';if(img.dataset.image){const button=img.closest('[data-figure]');button.click();img.src=document.querySelector('#dialog-image').src;document.querySelector('#dialog-close').click();delete img.dataset.image}})});
  await page.locator('.figure-panel img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.decode())));
  await page.emulateMedia({media:'print'});ensure(await page.locator('.pair .annotation').first().isVisible()&&await page.locator('.pair .translation').first().isVisible(),'Print content missing');
  report.errors=errors;report.remoteRequests=remote;ensure(!errors.length&&!remote.length,'Browser error or remote asset dependency');
  if(shots)fs.writeFileSync(path.join(shots,'report.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
