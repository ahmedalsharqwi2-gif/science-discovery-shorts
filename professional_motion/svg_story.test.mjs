import test from 'node:test';
import assert from 'node:assert/strict';
import {validateDiagram,diagramSvg} from './svg_story.js';
test('SVG diagrams use only explicit narration labels and change their active stage',()=>{
 const scene={narration:'دخول الهواء ثم خروج الهواء',diagram:{kind:'flow',nodes:[{label:'دخول الهواء'},{label:'خروج الهواء'}]}};
 const d=validateDiagram(scene);assert.notEqual(diagramSvg(d,0),diagramSvg(d,.9));assert.match(diagramSvg(d,.5),/دخول الهواء/);
 assert.throws(()=>validateDiagram({...scene,diagram:{...d,nodes:[{label:'حدث مختلق'},{label:'خروج الهواء'}]}}));
});
test('SVG content escapes markup and rejects unsupported chart types',()=>{
 assert.match(diagramSvg({kind:'comparison',nodes:[{label:'<script>'},{label:'نص'}]},0),/&lt;script&gt;/);
 assert.throws(()=>validateDiagram({narration:'أ ب',diagram:{kind:'invented',nodes:[{label:'أ'},{label:'ب'}]}}));
});
