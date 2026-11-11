(()=>{'use strict';
const body=document.body, nav=document.querySelector('.section-nav');
const setNavHeight=()=>document.documentElement.style.setProperty('--nav-height',nav.getBoundingClientRect().height+'px');
setNavHeight();new ResizeObserver(setNavHeight).observe(nav);
document.querySelectorAll('[data-category]').forEach(btn=>btn.addEventListener('click',()=>{const active=btn.getAttribute('aria-pressed')==='true';btn.setAttribute('aria-pressed',String(!active));body.classList.toggle('off-'+btn.dataset.category,active)}));
document.getElementById('show-cn').addEventListener('change',e=>body.classList.toggle('hide-cn',!e.target.checked));
document.getElementById('show-notes').addEventListener('change',e=>body.classList.toggle('hide-notes',!e.target.checked));
document.getElementById('jump').addEventListener('change',e=>{if(e.target.value){location.hash=e.target.value;e.target.value=''}});
const course=document.getElementById('course');try{const saved=localStorage.getItem(body.dataset.storageKey);if(saved)course.textContent=saved}catch(e){}
course.addEventListener('input',()=>{try{localStorage.setItem(body.dataset.storageKey,course.textContent.slice(0,150))}catch(e){}});
course.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();course.blur()}});
course.addEventListener('paste',e=>{e.preventDefault();const text=e.clipboardData.getData('text/plain').replace(/\s+/g,' ').slice(0,150);document.execCommand('insertText',false,text)});
const imgs=JSON.parse(document.getElementById('image-data').textContent);const pageKeys=Object.keys(imgs.pages).map(Number).sort((a,b)=>a-b);const pageCount=pageKeys.length;document.getElementById('image-data').remove();
const loadImage=img=>{if(!img.dataset.image)return;const [type,key]=img.dataset.image.split(':');img.loading='eager';img.src=imgs[type][key];delete img.dataset.image};
const lazy=new IntersectionObserver(entries=>entries.forEach(en=>{if(en.isIntersecting){loadImage(en.target);lazy.unobserve(en.target)}}),{rootMargin:'650px'});
document.querySelectorAll('img[data-image]').forEach(img=>lazy.observe(img));
const dialog=document.getElementById('source-dialog'),dImage=document.getElementById('dialog-image'),dScroll=document.getElementById('dialog-scroll');
let current=1,kind='pages';
function showSource(type,key,title){kind=type;current=type==='pages'?Number(key):String(key);document.getElementById('dialog-title').textContent=title||(type==='pages'?'原PDF · 第 '+current+' / '+pageCount+' 页':'论文源图 · PDF第'+current+'页');dImage.src=imgs[type][String(key)];dImage.alt=title||'原PDF第'+current+'页';dScroll.classList.remove('zoom');dScroll.scrollTop=0;document.getElementById('dialog-zoom').textContent='原始尺寸';document.getElementById('dialog-prev').disabled=type!=='pages'||current<=Math.min(...pageKeys);document.getElementById('dialog-next').disabled=type!=='pages'||current>=Math.max(...pageKeys);document.getElementById('dialog-footer').textContent=type==='pages'?'合并PDF第'+current+'页 · 来源：用户提供文件 · 可用左右箭头翻页':'原论文图版 · 合并PDF第'+(imgs.figure_pages?.[String(key)]||key)+'页';if(!dialog.open)dialog.showModal()}
document.addEventListener('click',e=>{const p=e.target.closest('[data-page]'),f=e.target.closest('[data-figure]');if(p)showSource('pages',p.dataset.page);if(f)showSource('figures',f.dataset.figure,f.dataset.title+' · 源图')});
document.getElementById('dialog-close').addEventListener('click',()=>dialog.close());
document.getElementById('dialog-prev').addEventListener('click',()=>{if(kind==='pages'&&current>Math.min(...pageKeys))showSource('pages',current-1)});
document.getElementById('dialog-next').addEventListener('click',()=>{if(kind==='pages'&&current<Math.max(...pageKeys))showSource('pages',current+1)});
document.getElementById('dialog-zoom').addEventListener('click',e=>{const on=dScroll.classList.toggle('zoom');e.target.textContent=on?'适合窗口':'原始尺寸'});
dialog.addEventListener('keydown',e=>{if(kind==='pages'&&e.key==='ArrowLeft'&&current>Math.min(...pageKeys)){e.preventDefault();showSource('pages',current-1)}if(kind==='pages'&&e.key==='ArrowRight'&&current<Math.max(...pageKeys)){e.preventDefault();showSource('pages',current+1)}});
dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
let printRefsOpen=false,printing=false;function beforePrint(){if(!printing){printRefsOpen=document.querySelector('.reference-details').open;printing=true}document.querySelector('.reference-details').open=true;document.querySelectorAll('.figure-panel img[data-image]').forEach(loadImage)}function afterPrint(){document.querySelector('.reference-details').open=printRefsOpen;printing=false}
window.addEventListener('beforeprint',beforePrint);window.addEventListener('afterprint',afterPrint);document.getElementById('print').addEventListener('click',async()=>{beforePrint();await Promise.all([...document.querySelectorAll('.figure-panel img')].map(img=>img.decode().catch(()=>{})));window.print()});
const progress=document.getElementById('progress'),links=[...document.querySelectorAll('.nav-links a')],targets=links.map(a=>document.querySelector(a.getAttribute('href')));let scheduled=false;
function updateScroll(){scheduled=false;const max=document.documentElement.scrollHeight-innerHeight;progress.style.width=(max>0?100*scrollY/max:0)+'%';let active=0,best=-Infinity;const cutoff=nav.getBoundingClientRect().height+55;targets.forEach((t,i)=>{if(t){const top=t.getBoundingClientRect().top;if(top<=cutoff&&top>best){best=top;active=i}}});links.forEach((a,i)=>{a.classList.toggle('active',i===active);if(i===active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')})}
addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(updateScroll)}},{passive:true});updateScroll();
const search=document.getElementById('search'),count=document.getElementById('search-count'),pairs=[...document.querySelectorAll('.pair')];let matches=[],index=-1,timer;
function move(delta){if(!matches.length)return;document.querySelectorAll('.search-hit').forEach(el=>el.classList.remove('search-hit'));index=(index+delta+matches.length)%matches.length;const el=matches[index];el.classList.add('search-hit');el.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});count.textContent=(index+1)+' / '+matches.length}
function find(){document.querySelectorAll('.search-hit').forEach(el=>el.classList.remove('search-hit'));const q=search.value.trim().toLocaleLowerCase();matches=q?pairs.filter(el=>el.textContent.toLocaleLowerCase().includes(q)):[];index=-1;count.textContent=q?'0 / '+matches.length:'';document.getElementById('search-prev').disabled=!matches.length;document.getElementById('search-next').disabled=!matches.length}
search.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(find,180)});search.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();clearTimeout(timer);if(index===-1)find();move(e.shiftKey?-1:1)}if(e.key==='Escape'){search.value='';find()}});document.getElementById('search-next').addEventListener('click',()=>move(1));document.getElementById('search-prev').addEventListener('click',()=>move(-1));find();
})();
