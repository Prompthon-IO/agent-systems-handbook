import React from 'react';
import {Composition, registerRoot} from 'remotion';
import brief from '../brief.json';
import {Promotion, type Brief} from './Promotion';

const Root = () => <Composition
  id="Promotion"
  component={Promotion}
  defaultProps={brief as Brief}
  width={brief.width}
  height={brief.height}
  fps={brief.fps}
  durationInFrames={brief.scenes.reduce((sum, scene) => sum + Math.round(scene.duration * brief.fps), 0)}
  calculateMetadata={({props}) => ({width: props.width, height: props.height, fps: props.fps,
    durationInFrames: props.scenes.reduce((sum, scene) => sum + Math.round(scene.duration * props.fps), 0)})}
/>;
registerRoot(Root);
