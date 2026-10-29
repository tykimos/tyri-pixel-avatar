#!/usr/bin/env node
'use strict';
/* Tyri Pixel Avatar by Taeyoung Kim (tykimos). See LICENSE. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
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
function encode(paths,durations,base,work,format='comparison'){
 const list=['ffconcat version 1.0'];
 paths.forEach((p,i)=>list.push("file '"+p.replace(/'/g,"'\\''")+"'",'option framerate 50','duration '+(durations[i]/1000).toFixed(3)));
 list.push("file '"+paths.at(-1).replace(/'/g,"'\\''")+"'",'option framerate 50');
 const timeline=path.join(work,path.basename(base)+'.ffconcat');fs.writeFileSync(timeline,list.join('\n')+'\n');
 const seconds=(durations.reduce((a,b)=>a+b,0)/1000).toFixed(3);
 if(format==='native'){
  // Explicit per-frame durations also preserve the final hold. The FFmpeg
  // animation encoder otherwise infers the last duration from the previous PTS.
  const source=path.join(work,'native-webp-frames.json');fs.writeFileSync(source,JSON.stringify({paths,durations}));
  const encoder=[
   'import json,sys',
   'from PIL import Image',
   'with open(sys.argv[1]) as f: source=json.load(f)',
   'frames=[]',
   'for path in source["paths"]:',
   ' with Image.open(path) as image: frames.append(image.convert("RGBA"))',
   'try:',
   ' frames[0].save(sys.argv[2],format="WEBP",save_all=True,append_images=frames[1:],duration=source["durations"],loop=0,lossless=True,quality=100,method=4,exact=True)',
   'finally:',
   ' for image in frames: image.close()'
  ].join('\n');
  execFileSync('python3',['-c',encoder,source,base+'.webp'],{stdio:['ignore','pipe','pipe']});
 }else{
  ffmpeg(['-f','concat','-safe','0','-i',timeline,'-filter_complex','split[s0][s1];[s0]palettegen=stats_mode=full:max_colors=256[p];[s1][p]paletteuse=dither=none',
   '-t',seconds,'-loop','0',base+'.gif']);
 }
 ffmpeg(['-f','concat','-safe','0','-i',timeline,'-vf','fps=50','-t',seconds,'-c:v','libx264','-crf',format==='native'?'16':'18','-preset','fast','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart','-an',base+'.mp4']);
}

function viewportCommands(commands,scale,x,y){
 return commands.map(command=>{
  const [a,b,c,d,e,f]=command.transform;
  return {...command,transform:[a*scale,b*scale,c*scale,d*scale,e*scale+x,f*scale+y]};
 });
}

function paint(ctx,commands,images,downsample=false){
 ctx.save();
 ctx.globalCompositeOperation='source-over';
 // Render each original sprite directly into its final output. Never resize an
 // already-rasterized 1024px scene. The native face remains an integer 1:1 copy.
 ctx.imageSmoothingEnabled=downsample;
 if(downsample)ctx.imageSmoothingQuality='high';
 for(const command of commands){
  ctx.setTransform(...command.transform);
  ctx.globalAlpha=command.opacity===undefined?1:command.opacity;
  ctx.drawImage(images[command.sprite],0,0);
 }
 ctx.restore();
}

async function main(){
 const images={};for(const [id,s] of Object.entries(manifest.sprites))images[id]=await loadImage(path.join(root,s.path));
 const faceCommands=player.getDrawCommands(manifest,'none',0);
 function scene(ctx,id,time,size,x,y,options){
  paint(ctx,viewportCommands(player.getDrawCommands(manifest,id,time,options),size/1024,x,y),images,true);
 }
 const head=manifest.head.transform;
 if(head[1]!==0||head[2]!==0||head[0]!==head[3]||head[0]<=0)throw new Error('Native preview requires an upright uniformly scaled face.');
 const nativeZoom=1/head[0];
 const nativeSize=Math.ceil(1024*nativeZoom/2)*2;
 const nativeX=Math.round(head[4]*nativeZoom)-head[4]*nativeZoom;
 const nativeY=Math.round(head[5]*nativeZoom)-head[5]*nativeZoom;
 const nativeFace=viewportCommands(faceCommands,nativeZoom,nativeX,nativeY)[0];
 if(Math.abs(nativeFace.transform[0]-1)>1e-12||Math.abs(nativeFace.transform[3]-1)>1e-12)throw new Error('The native face must not be resampled.');
 const work=fs.mkdtempSync(path.join(os.tmpdir(),'tyri-layered-previews-'));
 try{
  const parts=createCanvas(1380,650),pc=parts.getContext('2d');pc.fillStyle='#101821';pc.fillRect(0,0,1380,650);
  font(pc,30,true);pc.fillStyle='#ffc27d';pc.fillText('TYRI  /  SEPARATE SPRITES',32,54);
  ['FACE ONLY','HAND ONLY','COMPOSITE'].forEach((label,i)=>{roundBox(pc,22+i*458,90,434,500);font(pc,19,true);pc.fillStyle='#e9eef5';pc.fillText(label,44+i*458,128);});
  scene(pc,'none',0,412,32,146);scene(pc,'wave',0,412,490,146,{faceVisible:false});scene(pc,'wave',0,412,948,146);
  font(pc,17);pc.fillStyle='#a8b8c8';pc.fillText('One shared face. Hand sprites contain no face or hair.',32,628);
  fs.writeFileSync(path.join(out,'layered-parts.png'),parts.toBuffer('image/png'));

  const stages=[{id:'none',time:0,duration:800}];
  for(const id of ['wave','peace','shush','heart','write','think']){
   let elapsed=0;for(const f of manifest.animations[id].frames){stages.push({id,time:elapsed,duration:f.duration_ms});elapsed+=f.duration_ms;}
  }
  stages.push({id:'none',time:0,duration:800});
  const paths=[],nativePaths=[],durations=[];
  for(const [index,stage] of stages.entries()){
   const c=createCanvas(1280,840),ctx=c.getContext('2d');ctx.fillStyle='#101821';ctx.fillRect(0,0,1280,840);
   font(ctx,42,true);ctx.fillStyle='#ffc27d';ctx.fillText('TYRI',32,60);
   font(ctx,20);ctx.fillStyle='#b8c6d4';ctx.fillText('ONE FACE  /  INDEPENDENT HANDS',174,56);
   roundBox(ctx,24,104,604,652);roundBox(ctx,652,104,604,652);
   font(ctx,21,true);ctx.fillStyle='#dbe5ee';ctx.fillText('NO HANDS',48,144);ctx.fillStyle='#ffc27d';ctx.fillText(labels[stage.id],676,144);
   scene(ctx,'none',0,580,36,168);scene(ctx,stage.id,stage.time,580,664,168);
   font(ctx,18);ctx.fillStyle='#a8b8c8';ctx.fillText('Same face PNG, position and scale in every state.',32,800);
   font(ctx,15);ctx.fillText('Tyri Pixel Avatar by Taeyoung Kim (tykimos)',831,800);
   const file=path.join(work,'hero-'+String(index).padStart(3,'0')+'.png');fs.writeFileSync(file,c.toBuffer('image/png'));paths.push(file);durations.push(stage.duration);
   if(index===1)fs.writeFileSync(path.join(out,'layered-hero.png'),c.toBuffer('image/png'));
   const native=createCanvas(nativeSize,nativeSize),nc=native.getContext('2d');
   nc.fillStyle='#101821';nc.fillRect(0,0,nativeSize,nativeSize);
   const commands=viewportCommands(player.getDrawCommands(manifest,stage.id,stage.time),nativeZoom,nativeX,nativeY);
   const currentFace=commands.find(command=>command.isHead);
   if(JSON.stringify(currentFace.transform)!==JSON.stringify(nativeFace.transform))throw new Error('A state changed the native face.');
   paint(nc,commands,images);
   font(nc,Math.round(30*nativeZoom),true);nc.fillStyle='#ffc27d';nc.fillText('TYRI',32*nativeZoom,52*nativeZoom);
   font(nc,Math.round(17*nativeZoom));nc.fillStyle='#b8c6d4';nc.textAlign='right';nc.fillText(labels[stage.id],nativeSize-32*nativeZoom,48*nativeZoom);nc.textAlign='left';
   font(nc,Math.round(13*nativeZoom));nc.fillStyle='#a8b8c8';nc.fillText('Tyri Pixel Avatar by Taeyoung Kim (tykimos)',32*nativeZoom,nativeSize-22*nativeZoom);
   const nativeFile=path.join(work,'native-'+String(index).padStart(3,'0')+'.png');fs.writeFileSync(nativeFile,native.toBuffer('image/png'));nativePaths.push(nativeFile);
   if(index===1)fs.writeFileSync(path.join(out,'layered-native.png'),native.toBuffer('image/png'));
  }
  encode(paths,durations,path.join(out,'layered-hero'),work);
  encode(nativePaths,durations,path.join(out,'layered-native'),work,'native');
  const faceSprite=manifest.sprites[manifest.head.sprite];
  const report={schema:'tyri.preview-quality.v1',source:{path:faceSprite.path,file_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,faceSprite.path))).digest('hex'),canvas_size:faceSprite.source_size,content_bbox:faceSprite.content_bbox},native:{canvas_size:[nativeSize,nativeSize],face_transform:nativeFace.transform,face_pixels_per_source_pixel:1,face_resampling:'none; integer translation at original pixel size',animation:'previews/layered-native.webp',encoding:'lossless WebP',poster:'previews/layered-native.png',video:'previews/layered-native.mp4',video_encoding:'H.264 CRF 16; lossy compatibility copy'},comparison:{canvas_size:[1280,840],face_display_width:faceSprite.content_bbox[2]*head[0]*580/1024,sampling:'one direct high-quality downsample from original sprites',gif:'256-color comparison copy'},duration_ms:durations.reduce((a,b)=>a+b,0),source_frame_count:stages.length,face_transform_identical_in_all_states:true};
  fs.writeFileSync(path.join(root,'docs/preview-quality.json'),JSON.stringify(report,null,2)+'\n');
  fs.writeFileSync(path.join(work,'timeline.json'),JSON.stringify({stages,paths:nativePaths,durations},null,2)+'\n');
  console.log(JSON.stringify({...report,validation_frames:process.env.TYRI_PREVIEW_KEEP_FRAMES==='1'?work:undefined}));
 }finally{if(process.env.TYRI_PREVIEW_KEEP_FRAMES!=='1')fs.rmSync(work,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e.stack||e.message);process.exitCode=1;});
