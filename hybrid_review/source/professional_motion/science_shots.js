/** Pure deterministic shot paths: bounded, eased motion without random shake. */
const SHOTS=[
 {name:'establish',truck:[-.35,.35],dolly:[.7,-.4],crane:[-.05,.08]},
 {name:'approach',truck:[.25,-.2],dolly:[.3,-.5],crane:[0,.1]},
 {name:'detail',truck:[-.22,.22],dolly:[.2,-.25],crane:[.02,.08]},
 {name:'explain',truck:[.25,-.25],dolly:[.35,-.2],crane:[.08,-.02]},
 {name:'trace',truck:[-.3,.3],dolly:[.3,-.15],crane:[-.04,.08]},
 {name:'layers',truck:[.24,-.24],dolly:[.25,-.3],crane:[.02,.12]},
 {name:'context',truck:[-.28,.28],dolly:[.1,.45],crane:[0,.06]},
 {name:'resolve',truck:[.15,0],dolly:[-.2,.6],crane:[.08,0]}
];
export function scienceShot(index,progress){
 if(!Number.isInteger(index)||index<0||index>=SHOTS.length||!Number.isFinite(progress))throw Error('Invalid science shot');
 const s=SHOTS[index],p=Math.min(1,Math.max(0,progress)),e=p*p*(3-2*p);
 const mix=v=>v[0]+(v[1]-v[0])*e;
 return {name:s.name,truck:mix(s.truck),dolly:mix(s.dolly),crane:mix(s.crane),targetX:mix(s.truck)*.10,targetY:mix(s.crane)*.25};
}

