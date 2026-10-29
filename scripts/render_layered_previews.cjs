#!/usr/bin/env node
'use strict';
/* Tyri Pixel Avatar by Taeyoung Kim (tykimos). See LICENSE. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {execFileSync}=require('node:child_process');
const {createCanvas,loadImage,GlobalFonts}=require('@napi-rs/canvas');
const root=path.resolve(__dirname,'..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'data/layers.json'),'utf8'));
const player=require(path.join(root,'layered-player.js'));
const out=path.join(root,'previews');fs.mkdirSync(out,{recursive:true});
const regular='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';
const bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';
if(fs.existsSync(regular))GlobalFonts.registerFromPath(regular,'Tyri Sans');
if(fs.existsSync(bold))GlobalFonts.registerFromPath(bold,'Tyri Sans Bold');
const labels={none:'NO HANDS',wave:'WAVE',peace:'PEACE',shush:'SHUSH',heart:'HEART',write:'WRITE',think:'THINK'};

function font(ctx,size,bold=false){ctx.font=size+'px "'+(bold?'Tyri Sans Bold':'Tyri Sans')+'"';}
function roundBox(ctx,x,y,w,h){ctx.fillStyle='#17222e';ctx.strokeStyle='#334553';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(x,y,w,h,20);ctx.fill();ctx.stroke();}
function ffmpeg(args){execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-filter_threads','1','-filter_complex_threads','1',...args],{stdio:['ignore','pipe','pipe']});}
function encode(paths,durations,base,work){
 const list=['ffconcat version 1.0'];
 paths.forEach((p,i)=>list.push("file '"+p.replace(/'/g,"'\\''")+"'",'option framerate 50','duration '+(durations[i]/1000).toFixed(3)));
 list.push("file '"+paths.at(-1).replace(/'/g,"'\\''")+"'",'option framerate 50');
 const timeline=path.join(work,path.basename(base)+'.ffconcat');fs.writeFileSync(timeline,list.join('\n')+'\n');
 const seconds=(durations.reduce((a,b)=>a+b,0)/1000).toFixed(3);
 ffmpeg(['-f','concat','-safe','0','-i',timeline,'-filter_complex','split[s0][s1];[s0]palettegen=stats_mode=full:max_colors=256[p];[s1][p]paletteuse=dither=none',
  '-t',seconds,'-loop','0',base+'.gif']);
 ffmpeg(['-f','concat','-safe','0','-i',timeline,'-vf','fps=50','-t',seconds,'-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart','-an',base+'.mp4']);
}

async function main(){
 const images={};for(const [id,s] of Object.entries(manifest.sprites))images[id]=await loadImage(path.join(root,s.path));
 function scene(id,time,options){const c=createCanvas(1024,1024);player.drawContext(c.getContext('2d'),player.getDrawCommands(manifest,id,time,options),images);return c;}
 const face=scene('none',0);
 const work=fs.mkdtempSync(path.join(os.tmpdir(),'tyri-layered-previews-'));
 try{
  const parts=createCanvas(1380,650),pc=parts.getContext('2d');pc.fillStyle='#101821';pc.fillRect(0,0,1380,650);
  font(pc,30,true);pc.fillStyle='#ffc27d';pc.fillText('TYRI  /  SEPARATE SPRITES',32,54);
  ['FACE ONLY','HAND ONLY','COMPOSITE'].forEach((label,i)=>{roundBox(pc,22+i*458,90,434,500);font(pc,19,true);pc.fillStyle='#e9eef5';pc.fillText(label,44+i*458,128);});
  pc.imageSmoothingEnabled=false;
  pc.drawImage(face,32,146,412,412);pc.drawImage(scene('wave',0,{faceVisible:false}),490,146,412,412);pc.drawImage(scene('wave',0),948,146,412,412);
  font(pc,17);pc.fillStyle='#a8b8c8';pc.fillText('One shared face. Hand sprites contain no face or hair.',32,628);
  fs.writeFileSync(path.join(out,'layered-parts.png'),parts.toBuffer('image/png'));

  const stages=[{id:'none',time:0,duration:800}];
  for(const id of ['wave','peace','shush','heart','write','think']){
   let elapsed=0;for(const f of manifest.animations[id].frames){stages.push({id,time:elapsed,duration:f.duration_ms});elapsed+=f.duration_ms;}
  }
  stages.push({id:'none',time:0,duration:800});
  const paths=[],durations=[];
  for(const [index,stage] of stages.entries()){
   const c=createCanvas(1280,840),ctx=c.getContext('2d');ctx.fillStyle='#101821';ctx.fillRect(0,0,1280,840);
   font(ctx,42,true);ctx.fillStyle='#ffc27d';ctx.fillText('TYRI',32,60);
   font(ctx,20);ctx.fillStyle='#b8c6d4';ctx.fillText('ONE FACE  /  INDEPENDENT HANDS',174,56);
   roundBox(ctx,24,104,604,652);roundBox(ctx,652,104,604,652);
   font(ctx,21,true);ctx.fillStyle='#dbe5ee';ctx.fillText('NO HANDS',48,144);ctx.fillStyle='#ffc27d';ctx.fillText(labels[stage.id],676,144);
   ctx.imageSmoothingEnabled=false;ctx.drawImage(face,36,168,580,580);ctx.drawImage(scene(stage.id,stage.time),664,168,580,580);
   font(ctx,18);ctx.fillStyle='#a8b8c8';ctx.fillText('Same face PNG, position and scale in every state.',32,800);
   font(ctx,15);ctx.fillText('Tyri Pixel Avatar by Taeyoung Kim (tykimos)',831,800);
   const file=path.join(work,'hero-'+String(index).padStart(3,'0')+'.png');fs.writeFileSync(file,c.toBuffer('image/png'));paths.push(file);durations.push(stage.duration);
   if(index===1)fs.writeFileSync(path.join(out,'layered-hero.png'),c.toBuffer('image/png'));
  }
  encode(paths,durations,path.join(out,'layered-hero'),work);
  console.log(JSON.stringify({previews:['previews/layered-hero.gif','previews/layered-hero.mp4','previews/layered-hero.png','previews/layered-parts.png'],duration_ms:durations.reduce((a,b)=>a+b,0)}));
 }finally{fs.rmSync(work,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
