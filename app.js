const C=window.TYRI_CATALOG, $=id=>document.getElementById(id);
const modes={reactions:'리액션 18종 + 손동작',directions:'9방향 · 눈깜빡임',expressions:'표정 24종',visemes:'입 모양 12종',gestures:'손동작 12종',sources:'원본 시트'};
const images={};let mode='reactions',selected='idle',started=0,pausedAt=null,playing=true,lastKey='';
const ctx=$('canvas').getContext('2d');
async function loadSource(id){
 if(images[id])return images[id];
 const source=C.sources[id],sheet=document.createElement('canvas');sheet.width=source.width;sheet.height=source.height;
 const context=sheet.getContext('2d');
 images[id]=sheet;sheet.ready=false;
 try{
  const pieces=await Promise.all(source.parts.map(part=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve([part,image]);image.onerror=()=>reject(Error(part.path));image.src=part.path;})));
  for(const [part,image] of pieces)context.drawImage(image,part.rect[0],part.rect[1]);
  sheet.ready=true;
 }catch(e){$('info').textContent='조각을 읽지 못했습니다: '+e.message;}
 return sheet;
}
function choose(key){selected=key;started=performance.now();if(!playing)pausedAt=started;lastKey='';renderButtons();}
function setMode(id){mode=id;selected=id==='reactions'?'idle':id==='sources'?'approved':Object.keys(C.atlases[id].frames)[0];started=performance.now();if(!playing)pausedAt=started;renderButtons();}
function renderButtons(){
 $('modes').replaceChildren();for(const [id,label] of Object.entries(modes)){const b=document.createElement('button');b.textContent=label;b.className=id===mode?'active':'';b.onclick=()=>setMode(id);$('modes').append(b);}
 $('choices').replaceChildren();const choices=mode==='reactions'?C.reactions.map(r=>[r.id,r.label]):mode==='sources'?Object.keys(C.sources).map(k=>[k,k]):Object.keys(C.atlases[mode].frames).map(k=>[k,k]);
 for(const [key,label] of choices){const b=document.createElement('button');b.textContent=label;b.className=key===selected?'active':'';b.onclick=()=>choose(key);$('choices').append(b);}
}
$('play').onclick=()=>{const now=performance.now();if(playing){pausedAt=now;}else{started+=now-pausedAt;pausedAt=null;}playing=!playing;$('play').textContent=playing?'일시정지':'재생';};
$('reset').onclick=()=>setMode('reactions');
function draw(now){
 let source,rect,note='',elapsed=(playing?now:pausedAt)-started;
 if(mode==='reactions'){
  let r=C.reactions.find(r=>r.id===selected);let f=TyriPlayer.pickFrame(r.durations,elapsed,$('loop').checked||r.mode==='idle'||r.mode==='hold');
  if(f<0){selected='idle';started=now;r=C.reactions.find(r=>r.id==='idle');f=0;renderButtons();}
  source=r.source;rect=r.frames[f];note=r.note||'';
 }else if(mode==='sources'){source=selected;const s=C.sources[source];rect=[0,0,s.width,s.height];}
 else{source=C.atlases[mode].source;rect=C.atlases[mode].frames[selected];if(mode==='visemes')note='발음별 프레임 수동 확인. 음성과의 동기화 정확도는 별도 검증이 필요합니다.';}
 if(!images[source])loadSource(source);const im=images[source];if(im&&im.ready){
  const [x,y,w,h]=rect;const key=[source,x,y,w,h].join('/');if(lastKey!==key){
   const canvas=$('canvas');canvas.width=w;canvas.height=h;ctx.clearRect(0,0,w,h);ctx.drawImage(im,x,y,w,h,0,0,w,h);
   $('info').textContent=`${selected} · 원본 프레임 ${w} × ${h}px · ${source}`;$('note').textContent=note;$('source').href=C.sources[source].parts[0].path;$('source').textContent='이 시트의 첫 원본 조각 PNG';lastKey=key;
  }
 }
 requestAnimationFrame(draw);
}
setMode('reactions');requestAnimationFrame(draw);
