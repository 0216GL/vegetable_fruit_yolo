/* Quiet editorial pages. Home markup and its event bindings are untouched. */
(()=>{
const oldBind=bindCineInteractions;
const titles={recognize:['FRUIT OBSERVATORY','果实观察台'],roots:['WATER & ORCHARDS','山渠与果园'],about:['METHOD & EVIDENCE','方法与验证']};
const label=(en,cn)=>`<span>${en}</span><strong>${cn}</strong>`;
function refineRobot(root){root.querySelectorAll('.ow-robot').forEach(bot=>{
 bot.dataset.botMotion='grounded';const host=bot.closest('.xh-trail')||bot;host.onpointermove=null;host.onpointerleave=null;
 const reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;let action=null;
 const reply=()=>{if(reduce)return;action?.cancel();action=bot.animate([{transform:'translate(0,0) rotate(0deg)',offset:0},{transform:'translate(-2px,0) rotate(-3deg)',offset:.3},{transform:'translate(1px,1px) rotate(1.5deg)',offset:.62},{transform:'translate(0,0) rotate(0deg)',offset:1}],{duration:1150,easing:'cubic-bezier(.3,0,.25,1)'});};
 bot.addEventListener('click',reply);if(host!==bot)host.querySelector('.xh-ask')?.addEventListener('click',reply);
 root.querySelectorAll('[data-canal-scene],[data-question],[data-workflow],[data-record]').forEach(b=>b.addEventListener('click',reply));
})}

bindCineInteractions=function(){oldBind();const root=document.getElementById('app');if(route==='home'){root.classList.remove('rf-editorial');const hero=root.querySelector('.hero h1');if(hero)hero.textContent='太行果眸';const h=root.querySelector('#fx-title');if(h)h.textContent='山野果实';const s=root.querySelector('.dn-season h2');if(s)s.textContent='果色观察';return;}root.classList.add('rf-editorial');const t=titles[route];if(!t)return;
 const heading=root.querySelector('h1'),eyebrow=route==='recognize'?root.querySelector('.ow-heading .ow-eyebrow'):root.querySelector('section .dn-eyebrow');heading.textContent=t[1];heading.classList.add('rf-title');if(eyebrow)eyebrow.textContent=t[0];
 refineRobot(root);
 if(route==='recognize'){const title=root.querySelector('.ow-guide h2');title.textContent='拍照指引';root.querySelector('.ow-guide .ow-eyebrow').textContent='BEFORE THE SHUTTER';return}
 if(route==='roots'){
 const section=root.querySelector('.dn-land'),copy=section.querySelector('.dn-land-copy'),photo=section.querySelector('.dn-land-photo'),questions=section.querySelector('.dn-questions');section.classList.add('rf-field');copy.querySelector('h2').textContent='从采收到分选';copy.querySelector('.dn-eyebrow').textContent='IN THE ORCHARD';copy.querySelector('.dn-lede').textContent='把采集、分级与使用场景放在一起看。选择一个问题，展开具体记录。';const head=document.createElement('div');head.className='rf-field-head';head.append(copy.querySelector('.dn-eyebrow'),copy.querySelector('h2'),copy.querySelector('.dn-lede'));section.prepend(head);const tabs=document.createElement('div');tabs.className='rf-question-tabs';tabs.setAttribute('role','group');tabs.setAttribute('aria-label','选择果园观察问题');questions.querySelectorAll('[data-question]').forEach(b=>tabs.append(b));questions.prepend(tabs);copy.classList.add('rf-field-notes');photo.insertAdjacentHTML('beforeend','<span class="rf-photo-label">FIELD / 观察采收与分级</span>');const change=()=>{let selected=questions.querySelector('[aria-expanded="true"]');section.dataset.note=selected?.dataset.question||'0';photo.querySelector('.rf-photo-label').textContent=['FIELD / 旺季与人手','FIELD / 外观与标准','FIELD / 工具与现场'][+section.dataset.note];};tabs.querySelectorAll('button').forEach(b=>b.addEventListener('click',change));change();
 }
 if(route==='about'){
 const records=root.querySelector('.dn-records');records.classList.add('rf-records');records.querySelector('.dn-records-heading').innerHTML='<div class="rf-section-label">'+label('RESEARCH LOG','实验记录')+'</div><p>选择一项材料，查看方法、记录与边界。</p>';const preview=records.querySelector('.dn-record-preview'),media=records.querySelector('#dn-record-media');const refresh=()=>{let current=records.querySelector('[data-record][aria-pressed="true"]');const i=+current.dataset.record;preview.dataset.activeRecord=i;if(i===0){media.innerHTML='<div class="rf-grades"><span><i></i>未熟</span><span><i></i>转色期</span><span><i></i>着色期</span><span><i></i>完熟</span></div><small class="rf-media-note">四级外观标签 / 色块仅作目录标识</small>'}if(i===1){media.innerHTML='<div class="rf-data-row"><span>分类图像</span><b>443 张</b></div><div class="rf-data-row"><span>训练集</span><b>353 张</b></div><div class="rf-data-row"><span>验证集</span><b>90 张</b></div><div class="rf-data-row"><span>独立测试集</span><b>待补充</b></div>'}media.classList.remove('rf-switch');void media.offsetWidth;media.classList.add('rf-switch')};records.querySelectorAll('[data-record]').forEach(b=>b.addEventListener('click',refresh));refresh();
 }
};
})();
