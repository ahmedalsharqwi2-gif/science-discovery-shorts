import React from 'react';
import {Composition} from 'remotion';
import {Documentary} from './Documentary';
import template from '../../config/visual_template.json';
import type {Profile} from './types';
// No borrowed channel, stock story, invented logo or fallback hook.
// A caller supplies an authored episode using --props after preflight.
export const Root=()=> <Composition id="Documentary" component={Documentary} width={template.canvas.w} height={template.canvas.h} fps={template.canvas.fps} durationInFrames={template.canvas.fps} defaultProps={{episode:{profile:template.channel as Profile,series:template.display_name,title:'',duration:1,review_only:true,caption_groups:[],scenes:[]}}} calculateMetadata={({props})=>({durationInFrames:Math.ceil(props.episode.duration*template.canvas.fps)})}/>;
