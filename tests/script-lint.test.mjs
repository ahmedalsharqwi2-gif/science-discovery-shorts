import {test} from 'node:test';
import assert from 'node:assert/strict';
import {lintNarration} from '../pipeline/script-lint.mjs';

test('spelled-out year in scene text is rejected',()=>{
 const ep={hook:'هنشوف',cta:'تابعنا',scenes:[{text:'في ألفين وتسعة وعشرين حصل الإطلاق الأول للمحرك.'}]};
 const hits=lintNarration(ep);
 assert.equal(hits.length,1);
 assert.equal(hits[0].kind,'spelled_out_year');
});
test('year-like ألفين + one number word is rejected',()=>{
 const ep={hook:'هنشوف',cta:'تابعنا',scenes:[{text:'من ألفين وعشرة والتجارب شغالة.'}]};
 assert.ok(lintNarration(ep).some(h=>h.kind==='spelled_out_year'));
});
test('ordinary numbers in words pass',()=>{
 const ep={hook:'إزاي بيشتغل؟',cta:'تابعنا عشان المزيد',scenes:[{text:'المحرك بيحرق أربعمائة كيلو في الثانية وبيعدي خمسة وعشرين اختبار.'}]};
 assert.deepEqual(lintNarration(ep),[]);
});
test('dense transliterated foreign names in one sentence are rejected',()=>{
 const ep={hook:'هنشوف',cta:'تابعنا',scenes:[{text:'فريق من ناسا وشركة إل ثري هاريس ونوفا سبيس بيشتغلوا مع بعض.'}]};
 assert.ok(lintNarration(ep).some(h=>h.kind==='dense_transliterated_names'));
});
test('one foreign name per sentence passes',()=>{
 const ep={hook:'هنشوف',cta:'تابعنا',scenes:[{text:'ناسا بتختبر المحرك قبل الإطلاق. والفريق بيراجع كل جزء بعناية.'}]};
 assert.deepEqual(lintNarration(ep),[]);
});
test('two Latin-script names are rejected',()=>{
 const ep={hook:'هنشوف',cta:'تابعنا',scenes:[{text:'شركة NASA و L3Harris بيشتغلوا على المحرك.'}]};
 assert.ok(lintNarration(ep).some(h=>h.kind==='latin_names'));
});
test('claim and evidence are never linted',()=>{
 const ep={hook:'هنشوف',cta:'تابعنا',scenes:[{text:'جملة نظيفة تماماً عن المحرك.',claim:'في ألفين وتسعة وعشرين',evidence:'ناسا و إل ثري هاريس في ألفين وعشرين'}]};
 assert.deepEqual(lintNarration(ep),[]);
});
test('hook and cta are linted too',()=>{
 const ep={hook:'في ألفين وتسعة وعشرين إيه اللي حصل؟',cta:'تابعنا',scenes:[{text:'جملة نظيفة.'}]};
 assert.ok(lintNarration(ep).some(h=>h.field==='hook'));
});

test('lint: quantity with thousand-word is NOT a spelled-out year',()=>{
  const ep={hook:'',cta:'',scenes:[{text:'سار بجيش مكوَّن من عشرين ألف جُندي على الإبل.'}]};
  assert.deepEqual(lintNarration(ep).filter(i=>i.kind==='spelled_out_year'),[]);
});
test('lint: run starting with thousand-word IS a spelled-out year',()=>{
  const ep={hook:'',cta:'',scenes:[{text:'في مهمة أرتميس اللي متخطط لها في عام ألفين وثمانية وعشرين.'}]};
  assert.ok(lintNarration(ep).some(i=>i.kind==='spelled_out_year'||i.kind==='spelled_out_number_run'));
});

test('lint: adjacent quantities (ages nine and fourteen) are NOT a year',()=>{
  const ep={hook:'',cta:'',scenes:[{text:'وأعمارهم كانت بتتراوح ما بين تسعة وأربعة عشر سنة في أغلب المغامرات.'}]};
  assert.deepEqual(lintNarration(ep),[]);
});
test('lint: three-word year chain starting with thousand is still rejected',()=>{
  const ep={hook:'',cta:'',scenes:[{text:'ده حصل في ألفين وتسعة وعشرين تقريبًا.'}]};
  assert.ok(lintNarration(ep).some(i=>i.kind==='spelled_out_year'));
});
