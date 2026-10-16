import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {validateBrief} from './brief.mjs';
const mode=process.argv[2]??'preview';
if(!['check','preview','render'].includes(mode))throw new Error('Use check, preview or render.');
const root=process.cwd();
const brief=JSON.parse(await fs.readFile(path.join(root,'brief.json'),'utf8'));
const metadata=validateBrief(brief,root);
if(mode==='check'){
 console.log(JSON.stringify({status:'valid',...metadata,audio:brief.audio?.length?'supplied local audio':'silent',note:'Validation is not a render.'}));
}else{
 const browserExecutable=process.env.REMOTION_BROWSER_EXECUTABLE;
 if(!browserExecutable)throw new Error('Set REMOTION_BROWSER_EXECUTABLE to an installed Chrome/Chromium executable. No browser will be downloaded.');
 await fs.access(browserExecutable);
 const {bundle}=await import('@remotion/bundler');
 const {selectComposition,renderStill,renderMedia}=await import('@remotion/renderer');
 const serveUrl=await bundle({entryPoint:path.join(root,'src/index.tsx')});
 const composition=await selectComposition({serveUrl,id:'Promotion',inputProps:brief,browserExecutable});
 const directory=path.join(root,'output',new Date().toISOString().replace(/[:.]/g,'-')+'-'+mode+'-'+randomUUID().slice(0,8));
 await fs.mkdir(directory,{recursive:true});
 if(mode==='preview'){
   let start=0;const figures=[];
   for(let i=0;i<brief.scenes.length;i++){
     const duration=Math.round(brief.scenes[i].duration*brief.fps),frame=start+Math.floor(duration/2);
     const name=`scene-${i+1}.png`;
     await renderStill({serveUrl,composition,frame,output:path.join(directory,name),inputProps:brief,browserExecutable});
     figures.push(`<figure><img src="${name}"/><figcaption>Scene ${i+1}, frame ${frame}</figcaption></figure>`);start+=duration;
   }
   await fs.writeFile(path.join(directory,'preview.html'),'<!doctype html><meta charset="utf-8"><title>Local video preview</title><style>body{background:#17202c;color:white;font:16px Arial;display:flex;flex-wrap:wrap;gap:16px}figure{margin:12px}img{width:220px;max-height:420px;object-fit:contain}figcaption{padding:8px}</style><h1 style="width:100%">Scene midpoint preview</h1>'+figures.join(''));
 }else{
   await renderMedia({serveUrl,composition,codec:'h264',outputLocation:path.join(directory,'promotion.mp4'),inputProps:brief,browserExecutable,concurrency:1});
 }
 await fs.writeFile(path.join(directory,'brief.json'),JSON.stringify(brief,null,2));
 const receipt={status:mode==='render'?'rendered':'previewed',directory,...metadata,width:brief.width,height:brief.height,fps:brief.fps,
   audio:brief.audio?.length?'supplied local audio; listening not verified':'silent',visualReview:'not verified by renderer',remotion:'4.0.532'};
 await fs.writeFile(path.join(directory,'receipt.json'),JSON.stringify(receipt,null,2));
 console.log(JSON.stringify(receipt));
}
