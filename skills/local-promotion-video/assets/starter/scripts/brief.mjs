import fs from 'node:fs';
import path from 'node:path';
export function assetPath(root, value) {
  if(typeof value !== 'string' || !value || value.includes('\\') || value.split('/').includes('..') || value.startsWith('/') || /^[a-z]+:/i.test(value))
    throw new Error('Assets must use relative local paths inside public/.');
  const publicRoot=path.resolve(root,'public');
  const file=path.resolve(publicRoot,value);
  if(!file.startsWith(publicRoot+path.sep) || !fs.existsSync(file))throw new Error(`Local asset not found: ${value}`);
  const realRoot=fs.realpathSync(publicRoot), realFile=fs.realpathSync(file);
  if(!realFile.startsWith(realRoot+path.sep) || !fs.statSync(realFile).isFile())throw new Error('Asset resolves outside public/ or is not a file.');
  return file;
}
export function validateBrief(b,root) {
  if(!b || typeof b!=='object')throw new Error('brief.json must be an object.');
  for(const [key,max] of [['product',64],['audience',200]])if(typeof b[key]!=='string'||!b[key].trim()||b[key].length>max)throw new Error(`Invalid ${key}.`);
  for(const k of ['width','height'])if(!Number.isInteger(b[k])||b[k]<240||b[k]>3840||b[k]%2)throw new Error('Frame dimensions must be even integers between 240 and 3840.');
  if(!Number.isInteger(b.fps)||b.fps<12||b.fps>60)throw new Error('fps must be an integer from 12 to 60.');
  for(const k of ['background','accent'])if(!/^#[0-9a-f]{6}$/i.test(b[k]))throw new Error(`Use a six-digit hex ${k}.`);
  if(!Array.isArray(b.scenes)||b.scenes.length<1||b.scenes.length>8)throw new Error('Use one to eight scenes.');
  let total=0;
  for(const scene of b.scenes){
    if(!Number.isFinite(scene.duration)||scene.duration<=0||Math.round(scene.duration*b.fps)<1)throw new Error('Each scene needs at least one frame.');
    total+=Math.round(scene.duration*b.fps);
    if(typeof scene.heading!=='string'||!scene.heading.trim()||scene.heading.length>90)throw new Error('Scene heading must be 1–90 characters.');
    if(scene.body!==undefined&&(typeof scene.body!=='string'||scene.body.length>240))throw new Error('Shorten the scene body to 240 characters or split the scene.');
    if(scene.image)assetPath(root,scene.image);
    if(scene.checklist!==undefined&&(!Array.isArray(scene.checklist)||scene.checklist.length>4||scene.checklist.some(t=>typeof t!=='string'||!t||t.length>60)))throw new Error('Use up to four short checklist lines.');
  }
  if(total/b.fps<1||total/b.fps>120)throw new Error('This small starter supports 1–120 seconds.');
  if(b.audio!==undefined&&!Array.isArray(b.audio))throw new Error('audio must be an array.');
  for(const audio of b.audio??[]){
    assetPath(root,audio.file);
    if(!['music','voiceover'].includes(audio.kind)||!Number.isFinite(audio.volume)||audio.volume<0||audio.volume>1)throw new Error('Audio needs a kind and volume between 0 and 1.');
  }
  return {frames:total,durationSeconds:total/b.fps};
}
