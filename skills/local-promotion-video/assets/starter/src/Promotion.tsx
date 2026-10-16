import React from 'react';
import {AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';

type Scene = {duration: number; heading: string; body?: string; image?: string; checklist?: string[]};
export type Brief = {product: string; audience: string; width: number; height: number; fps: number;
  background: string; accent: string; scenes: Scene[]; audio?: {file: string; kind: 'music'|'voiceover'; volume: number}[]};

const Shot = ({scene, product, accent, background}: {scene: Scene; product: string; accent: string; background: string}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const portrait = height > width;
  const unit = width / 720;
  const heading = (portrait ? 62 : 44) * unit;
  return <AbsoluteFill style={{backgroundColor: background, color: '#F6F7F9', fontFamily: 'Arial, "Noto Sans CJK SC", sans-serif',
    padding: `${portrait ? 110 : 44}px ${54*unit}px`, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 30*unit}}>
    <div style={{color: accent, fontSize: 25*unit, fontWeight: 700, letterSpacing: 1}}>{product}</div>
    <div style={{display:'flex', flexDirection:'column', gap:28*unit,
      opacity: interpolate(frame,[0,10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}),
      translate: `0 ${interpolate(frame,[0,12],[18,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}px`}}>
      <h1 style={{fontSize:heading,lineHeight:1.14,margin:0,fontWeight:800,overflowWrap:'anywhere'}}>{scene.heading}</h1>
      {scene.body && <p style={{fontSize:30*unit,lineHeight:1.4,color:'#CBD2DC',margin:0,overflowWrap:'anywhere'}}>{scene.body}</p>}
      {scene.image && <Img src={staticFile(scene.image)} style={{width:'100%',maxHeight:height*.39,objectFit:'contain',borderRadius:18}}/>}
      {scene.checklist && <div style={{display:'flex',flexDirection:'column',gap:22*unit,padding:28*unit,background:'#1C2633',borderRadius:18}}>
        {scene.checklist.map((item,index)=><div key={index} style={{display:'flex',gap:18*unit,alignItems:'center',fontSize:29*unit,
          opacity:interpolate(frame,[12+index*14,22+index*14],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
          <span style={{color:accent}}>✓</span><span>{item}</span></div>)}
      </div>}
    </div>
  </AbsoluteFill>;
};

export const Promotion = (brief: Brief) => {
  let start=0;
  return <AbsoluteFill style={{backgroundColor:brief.background}}>
    {brief.scenes.map((scene,index)=>{
      const duration=Math.round(scene.duration*brief.fps);
      const from=start; start+=duration;
      return <Sequence key={index} from={from} durationInFrames={duration}>
        <Shot scene={scene} product={brief.product} accent={brief.accent} background={brief.background}/>
      </Sequence>;
    })}
    {(brief.audio??[]).map((audio,index)=><Audio key={index} src={staticFile(audio.file)} volume={audio.volume}/>)}
  </AbsoluteFill>;
};
