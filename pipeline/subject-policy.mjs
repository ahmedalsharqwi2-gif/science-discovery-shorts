// Route from the scene focus; incidental Earth references must not change the subject.
export function scientificSubject(scene){
 const declared=scene.diagramKind;if(['galaxy','star','cluster','planet','concept','light'].includes(declared))return declared;
 const focus=[scene.title||'',...(scene.labels||[])].join(' '),context=scene.text||'';
 if(/تجمع.*نجم|عنقود.*نجم|star.?cluster|NGC\s*206/i.test(focus))return 'cluster';
 if(/مساف|سنة ضو|سنه ضو|light.?year|رحلة الضوء/i.test(focus))return 'light';
 if(/مجر|galax/i.test(focus))return 'galaxy';
 if(/نجم|نجوم|شمس|stellar|\bstar\b|\bsun\b/i.test(focus))return 'star';
 if(/كوكب|سطح.*الأرض|قارات|جغراف|\bearth\b|\bplanet\b/i.test(focus))return 'planet';
 if(/\bNGC\s*\d+/i.test(focus)&&/مجر|galax/i.test(context))return 'galaxy';
 return 'concept';
}
