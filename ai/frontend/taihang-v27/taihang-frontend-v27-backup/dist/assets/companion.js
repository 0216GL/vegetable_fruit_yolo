/* Shared Xiaohe companion and editorial photo practice; workbench remains intact. */
(()=>{
const previousBind=bindCineInteractions;
const tips={roots:['沿着渠墙的走向，看水路怎样贴着山体延伸。','换一个视角，留意崖壁、步道与渠道的关系。','往下看看：山水之外，还有采收和分选的具体问题。'],about:['点选技术路径，可以查看每一步实际负责什么。','验证集成绩和真实现场效果，需要分开看。','下方档案可以查看数据划分、实验记录与目前的限制。']};
function mount(root){
 const host=document.createElement('aside');host.className='xh-trail';host.setAttribute('aria-label','小禾观察伙伴');host.innerHTML=`<div class="xh-trail-inner"><button class="ow-robot xh-trail-robot" aria-label="问问小禾，切换观察提示"><img src="assets/xiaohe-robot.png" alt="小禾果园巡检机器人"><span class="ow-robot-shadow"></span><span class="ex-eye ex-eye-0" aria-hidden="true"></span><span class="ex-eye ex-eye-1" aria-hidden="true"></span></button><div class="xh-note"><span>小禾 / 陪你观察</span><p aria-live="polite">${tips[route][0]}</p><button class="xh-ask">再问一句 ↗</button></div></div>`;
 root.querySelector('section').append(host);let n=0;const bot=host.querySelector('.ow-robot'),text=host.querySelector('p');const speak=(line)=>{text.textContent=line;bot.classList.remove('respond');void bot.offsetWidth;bot.classList.add('respond')};host.querySelector('.xh-ask').onclick=bot.onclick=()=>speak(tips[route][++n%tips[route].length]);bot.onanimationend=()=>bot.classList.remove('respond');
 const reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;
 if(!reduce&&matchMedia('(pointer:fine)').matches){host.onpointermove=e=>{let r=host.getBoundingClientRect();host.style.setProperty('--look',`${Math.max(-4,Math.min(4,(e.clientX-r.left-r.width/2)/40))}deg`)};host.onpointerleave=()=>host.style.setProperty('--look','0deg')}
 root.querySelectorAll('[data-canal-scene],[data-question],[data-workflow],[data-record]').forEach(b=>b.addEventListener('click',()=>{const label=b.querySelector('b')?.textContent||b.textContent.replace(/＋/g,'').trim();speak('一起看看「'+label+'」。')}));
}
bindCineInteractions=function(){previousBind();const root=document.getElementById('app');if(route==='roots'||route==='about')mount(root);if(route==='recognize'){
 const guide=root.querySelector('.ow-guide');if(!guide)return;guide.classList.add('xh-photo-practice');guide.querySelector('.ow-guide-photo').hidden=true;const photo=guide.querySelector('.ow-mini-example');photo.classList.add('xh-camera');photo.insertAdjacentHTML('beforeend','<div class="xh-frame" aria-hidden="true"><i></i><i></i><i></i><i></i></div><span class="xh-camera-label">拍照练习 / 展示照片</span>');guide.querySelector('h2').innerHTML='先看清，<br>再按下快门。';guide.querySelector('.ow-guide-lead').textContent='试着换一种观察重点，给下一张照片留一点余地。';guide.querySelectorAll('[data-ow-tip]').forEach(b=>b.addEventListener('click',()=>{guide.dataset.practice=b.dataset.owTip;const image=guide.querySelector('#ow-tip-image');image.style.transform='none';image.style.objectPosition='center';}));guide.dataset.practice='0';
 }};
})();
