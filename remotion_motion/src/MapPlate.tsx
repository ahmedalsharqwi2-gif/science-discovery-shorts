import React,{useEffect,useRef,useState} from 'react';
import {continueRender,delayRender,staticFile} from 'remotion';
import * as maplibre from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
export const MapPlate=({longitude=25,latitude=5,zoom=2.4,color='#dfbc79',marker=true}:{longitude?:number;latitude?:number;zoom?:number;color?:string;marker?:boolean})=>{
 const ref=useRef<HTMLDivElement>(null);const [handle]=useState(()=>delayRender('Load offline Natural Earth map'));
 useEffect(()=>{if(!ref.current)return;
  maplibre.setWorkerUrl(staticFile('maplibre-worker.mjs'));
  const map=new maplibre.Map({container:ref.current,center:[longitude,latitude],zoom,interactive:false,fadeDuration:0,attributionControl:false,canvasContextAttributes:{preserveDrawingBuffer:true},style:{version:8,sources:{world:{type:'geojson',data:staticFile('world.json')}},layers:[{id:'sea',type:'background',paint:{'background-color':'#101f2a'}},{id:'land',type:'fill',source:'world',paint:{'fill-color':'#243e46','fill-opacity':1}},{id:'coasts',type:'line',source:'world',paint:{'line-color':'#66847e','line-width':1.2,'line-opacity':.7}}]}});
  map.on('error',e=>console.error('Offline map error',e.error?.message));
  map.on('load',()=>{if(marker){map.addSource('point',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[longitude,latitude]}}});map.addLayer({id:'point-halo',type:'circle',source:'point',paint:{'circle-radius':28,'circle-color':color,'circle-opacity':.16}});map.addLayer({id:'point-core',type:'circle',source:'point',paint:{'circle-radius':7,'circle-color':color,'circle-stroke-width':3,'circle-stroke-color':'#ffffff'}});}map.jumpTo({center:[longitude,latitude],zoom});map.once('idle',()=>continueRender(handle));});
 },[handle,longitude,latitude,zoom,color,marker]);
 return <div ref={ref} style={{position:'absolute',inset:0}}/>;
};
