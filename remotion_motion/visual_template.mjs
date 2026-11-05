import fs from 'node:fs/promises';
import path from 'node:path';
export async function loadTemplate(project){
 const t=JSON.parse(await fs.readFile(path.join(project,'../config/visual_template.json')));
 const c=JSON.parse(await fs.readFile(path.join(project,'../config/channel_identity.json')));
 if(!Number.isInteger(t.version)||t.version!==1||!t.locked||!t.safe_zone||t.canvas?.w!==1080||t.canvas?.h!==1920||t.canvas?.fps!==30)throw Error('Missing, malformed or unsupported locked template');
 if(t.channel!==c.profile||t.display_name!==c.name||c.schedule_and_publication_configuration_changed!==false)throw Error('Channel identity or publication binding changed');
 for(const[a,b]of[['background','bg'],['ink','ink'],['accent','accent']])if(c[a]!==t.palette[b])throw Error('Locked palette conflict');
 return t;
}
