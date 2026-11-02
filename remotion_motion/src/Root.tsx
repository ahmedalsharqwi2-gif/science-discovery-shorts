import React from 'react';
import {Composition} from 'remotion';
import {Documentary} from './Documentary';
export const Root=()=> <Composition id="Documentary" component={Documentary} width={1080} height={1920} fps={30} durationInFrames={300} defaultProps={{episode:{profile:'history',series:'نقص ونروى',title:'إنقاذ أبو سمبل',duration:10,review_only:true,caption_groups:[],scenes:[{id:'setup',label:'معبد انتقل من مكانه',narration:'',start:0,end:10,kind:'photo',asset:'media/history-lift.jpg',asset_label:'صورة أرشيفية • Per-Olow Anderson / Public domain'}]}}} calculateMetadata={({props})=>({durationInFrames:Math.ceil(props.episode.duration*30)})}/>;
