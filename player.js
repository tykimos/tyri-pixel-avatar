/* Tyri / 타이리: frame selection only, no low-resolution fallback. */
(function(root){
  function pickFrame(durations, elapsed, loop) {
    const total=durations.reduce((a,b)=>a+b,0);
    if(!total || durations.some(x=>!Number.isFinite(x)||x<=0)) throw Error('Invalid timing');
    if(!loop && elapsed>=total) return -1;
    let t=Math.max(0,elapsed)%total;
    for(let i=0;i<durations.length;i++){if(t<durations[i])return i;t-=durations[i];}
    return durations.length-1;
  }
  const api={pickFrame};
  if(typeof module!=='undefined')module.exports=api;
  root.TyriPlayer=api;
})(globalThis);
