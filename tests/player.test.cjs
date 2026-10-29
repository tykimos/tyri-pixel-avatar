const test=require('node:test'),assert=require('node:assert/strict');
const {pickFrame}=require('../player.js');
test('one-shot returns to idle exactly at end',()=>{assert.equal(pickFrame([700,240],0,false),0);assert.equal(pickFrame([700,240],700,false),1);assert.equal(pickFrame([700,240],940,false),-1);});
test('hold/idle loops without undefined frames',()=>{for(let t=0;t<10000;t+=17)assert.ok([0,1].includes(pickFrame([850,180],t,true)));assert.equal(pickFrame([850,180],1030,true),0);});
test('invalid timing is rejected',()=>assert.throws(()=>pickFrame([0],10,true)));
