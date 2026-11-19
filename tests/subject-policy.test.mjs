import {test} from 'node:test';import assert from 'node:assert/strict';import {scientificSubject} from '../pipeline/subject-policy.mjs';
test('galaxy references cannot become Earth despite mentioning distance from Earth',()=>{assert.equal(scientificSubject({title:'المجرة الحلزونية NGC 4559',text:'المجرة بعيدة عن الأرض',labels:[]}), 'galaxy');});
test('a generic company map is a concept graph, never a planet',()=>{assert.equal(scientificSubject({title:'خريطة أدوات الشركة',text:'خطوات استخدام أدوات الذكاء الاصطناعي',labels:['بحث','نتيجة']}),'concept');assert.equal(scientificSubject({title:'سطح كوكب الأرض',text:'',labels:[]}),'planet');});

test('NGC206 is a star cluster and incidental host galaxy does not replace scene focus',()=>{assert.equal(scientificSubject({title:'التجمع النجمي NGC 206',text:'داخل مجرة أندروميدا',labels:[]}), 'cluster');assert.equal(scientificSubject({title:'هوية النجم المتفجر',text:'في مجرة NGC4559',labels:[]}), 'star');});
test('distance from Earth is a light path, not a map of Earth',()=>assert.equal(scientificSubject({title:'المسافة عن الأرض',text:'رحلة الضوء',labels:[]}), 'light'));
