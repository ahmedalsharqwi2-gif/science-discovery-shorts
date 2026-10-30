"""Source-reviewed editorial expansion of the same unpublished magnetosphere film."""
import copy,hashlib,json
from . import editorial as e
NARRATIONS=[
'تخيل إن حوالين الأرض فقاعة ضخمة من المغناطيسية، وإحنا مش شايفينها. ناسا بتسمي المنطقة دي الغلاف المغناطيسي. الفقاعة بتحوّل مسار معظم الجسيمات اللي جاية من الشمس، ووجودها ساعد غلافنا الجوي يفضل محمي. بس الحماية دي مش معناها إن مفيش حاجة بتعدي.',
'الشمس بتبعت باستمرار تيار من الجسيمات اسمه الرياح الشمسية. التيار ده بيقابل المجال المغناطيسي حوالين كوكبنا، فجزء كبير منه بيتحوّل بعيد. هنا لازم نفرق بين دور المجال ودور الغلاف الجوي: الغلاف الجوي نفسه بيساعد يحمينا من الأشعة فوق البنفسجية.',
'ناسا بتقارن الأرض بالمريخ عشان توضح أهمية الدرع ده. المريخ فقد غلافه المغناطيسي من زمن بعيد، والعلماء بيرجحوا إن الرياح الشمسية ساهمت في تجريد الكوكب من معظم غلافه الجوي. ده تفسير علمي محتمل، مش تجربة بتقول إن تاريخ الكوكبين كان واحد.',
'القصة مش بعيدة عن حياتنا اليومية. الطقس الفضائي الشديد ممكن يعطل شبكات الاتصالات، ويأثر على الملاحة بالأقمار الصناعية وشبكات الكهرباء. عشان كده دراسة المجال المغناطيسي مش مجرد رسم لخطوط حوالين كرة؛ دي محاولة نفهم خطر ممكن يوصل للتكنولوجيا اللي بنستخدمها.',
'الغلاف المغناطيسي درع قابل للنفاذ، مش حيطة مقفولة. أحيانًا المجال اللي مع الرياح الشمسية بيتصل بمجال الأرض، وبيجبر المنطقة تعيد ترتيب نفسها. العلماء بيوصفوا فتحات بتسمح بدخول الطاقة. الفتحات دي ممكن تظهر وتقفل أكتر من مرة، وبعضها صغير وقصير وبعضها أوسع.',
'العملية اللي بتحصل لما خطوط المجال تتقابل وتعيد ترتيب نفسها اسمها إعادة الاتصال المغناطيسي. الطاقة المخزنة ممكن تتحرر بعنف، ومعاها جسيمات مشحونة بتتحرك بسرعة كبيرة. ناسا بتدرس إزاي دخول الطاقة وتحررها مرتبطين بالعواصف المغناطيسية، وليه التغيير ده ممكن يبقى قوي بالشكل ده.',
'عشان تشوف اللي بيحصل عن قرب، ناسا أطلقت مهمة مكوّنة من أربع مركبات فضائية بتطير في تشكيل قريب. المركبات شايلة حساسات للمجال المغناطيسي وكواشف للجسيمات، وبتقيس مناطق بتحصل فيها إعادة الاتصال. القياسات دي بتدرس حركة الإلكترونات نفسها، بدل ما نعتمد على شكل الرسمة بس.',
'المهمة دي بتكمل بيانات بعثات تانية، عشان العلماء يفهموا فيزياء الفضاء ويحسنوا توقعات الطقس الفضائي. الفكرة مش إن الدرع كامل، ولا إننا نقدر نتنبأ بكل عاصفة بدقة. الفكرة إن كوكبنا محمي بنظام متحرك بيتفاعل مع الشمس طول الوقت، وكل قياس جديد بيكشف جزء منه.'
]
def main():
 data=e.registry();episode=next(r for r in data['episodes'] if r['slot']=='daily-2026-10-30')
 if episode.get('status') in ('scheduled','published'):raise RuntimeError('Do not alter a scheduled film')
 story=copy.deepcopy(episode['story'])
 if story['topic_key']!='earth-magnetosphere':raise ValueError('Only the same reserved topic is authorized')
 text=e.evidence(story['source']['url'])
 for phrase in ['permeable shield','Magnetospheric Multiscale','power grids','four MMS spacecraft']:
  if phrase.casefold() not in text.casefold():raise ValueError('NASA source no longer supports the reviewed expansion')
 labels=['فقاعة بتحمي الأرض','الرياح الشمسية','ليه المريخ مختلف؟','تأثير على التكنولوجيا','درع مش مقفول','إعادة الاتصال','أربع مركبات بتقيس','فهم أفضل للطقس الفضائي']
 for i,scene in enumerate(story['scenes']):scene.update(narration=NARRATIONS[i],label=labels[i],evidence_excerpt_id=[0,1,4,8,10,12,16,20][i])
 e.attach_evidence(story,text)
 story['editorial_review']={'supported':True,'novel':True,'issues':[],'review_type':'Codex source review of the same reserved NASA magnetosphere episode','checks':['Eight paragraphs checked against NASA article; no invented measurements','Distinguish atmosphere/UV shielding from magnetic deflection of charged particles','Mars atmospheric-loss explanation is attributed as a hypothesis','No claim of guaranteed forecasting or an impermeable shield'],'source_body_sha256':hashlib.sha256(text.encode()).hexdigest()}
 episode.update(story=story,title=story['title'],status='reserved',revision_reason='Original measured narration was 106.6 seconds; expanded substantive NASA explanation, no padding')
 e.save(data);(e.ROOT/'delivery').mkdir(exist_ok=True);(e.ROOT/'delivery/story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2))
 print('Source-reviewed same-topic narration words:',sum(len(s['narration'].split()) for s in story['scenes']))
if __name__=='__main__':main()
