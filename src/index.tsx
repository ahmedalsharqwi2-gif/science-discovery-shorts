import React from 'react';
import {Composition,registerRoot} from 'remotion';
import {Episode,type EpisodeProps} from './Episode';
import {PaperEpisode} from './paper/PaperEpisode';
const W=1080,H=1920;
const demo:EpisodeProps={title:'معاينة القوالب',durationInFrames:300,preview:true,scenes:[{title:'كل فكرة ليها حكاية',text:'',summary:'معاينة تصميم فقط',keyword:'فكرة',template:'phenomenon',labels:['بداية','نتيجة'],values:[],kind:'illustration',duration:10,words:[],expression:0,action:'point'}]};
const Routed=(props:any)=>props.paper&&props.paper.plan?<PaperEpisode {...props}/>:<Episode {...props}/>;
registerRoot(()=> <Composition id="Episode" component={Routed} width={W} height={H} fps={30} durationInFrames={300} defaultProps={demo} calculateMetadata={({props})=>({durationInFrames:(props as any).durationInFrames})}/>);
