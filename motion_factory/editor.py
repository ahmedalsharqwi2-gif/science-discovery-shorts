"""Six explainable scenes, grounded in a supplied brief or current official news."""
import json
from pathlib import Path

BRANDS = {'science': 'اسرار الكون', 'history': 'نقص ونروى', 'horror': 'ملفات غامضه', 'news': 'ai على السريع'}
KINDS = {'science': ['octopus', 'pigment', 'nerve', 'layers', 'camouflage', 'octopus'],
         'history': ['canal', 'route', 'excavation', 'canal', 'timeline', 'route'],
         'horror': ['lake', 'layers', 'gas', 'valley', 'pipe', 'lake'],
         'news': ['network', 'chip', 'comparison', 'flow', 'timeline', 'network']}
BRIEFS = {
 'science': {'title': 'الأخطبوط بيغير لونه إزاي؟', 'publisher': 'Smithsonian Ocean',
 'url': 'https://ocean.si.edu/ocean-life/invertebrates/how-octopuses-and-squids-change-color',
 'facts': ['Octopuses have pigment-containing chromatophores in their skin.', 'Muscles controlled by nerves expand or contract the pigment sacs, changing their visible area.', 'Reflective skin cells also contribute to appearance by interacting with light.', 'The nervous system coordinates patterns across the skin.', 'Color and texture changes can help camouflage and communication.', 'The diagrams are simplified illustrations, not microscope footage.']},
 'history': {'title': 'قناة السويس غيرت طريق السفن إزاي؟', 'publisher': 'Suez Canal Authority',
 'url': 'https://www.suezcanal.gov.eg/English/About/SuezCanal/Pages/CanalHistory.aspx',
 'facts': ['The Suez Canal connects the Mediterranean Sea and Red Sea through Egypt.', 'It offers a sea route between Europe and Asia without sailing around southern Africa.', 'Construction began in 1859 and involved severe human hardship; do not invent casualty statistics.', 'The canal opened in November 1869.', 'Egypt nationalized the canal in July 1956; distinguish nationalization from its original opening.', 'The canal is strategically important; the map is schematic and not for navigation.']},
 'horror': {'title': 'بحيرة نيوس: الخطر اللي مكنش باين', 'publisher': 'NASA Earth Observatory',
 'url': 'https://science.nasa.gov/earth/earth-observatory/lake-nyos-cameroon-86244/',
 'facts': ['Lake Nyos in Cameroon released a deadly cloud of carbon dioxide on 21 August 1986.', 'Gas accumulated in deep lake water over time.', 'Carbon dioxide is invisible; never portray a colored cloud as actual historical evidence.', 'Gas flowed into low-lying areas; more than seventeen hundred people died. Do not invent victim dialogue or a definite initial trigger.', 'Controlled degassing pipes were installed beginning in 2001 to gradually release accumulated gas.', 'Explain the physical mechanism, distinguish uncertainty, and never invent supernatural causes or claim risk disappeared.']}}


def validate(plan, profile):
    scenes = plan.get('scenes', [])
    if len(scenes) != 6:
        raise ValueError('Exactly six explanatory scenes are required')
    for index, scene in enumerate(scenes):
        if not 25 <= len(scene.get('narration', '').split()) <= 65:
            raise ValueError('Each scene needs 25–65 spoken words')
        cue = scene.get('cue', '')
        if not cue or cue not in scene['narration']:
            raise ValueError('Scene cue must occur verbatim in narration')
        if not scene.get('title') or len(scene['title']) > 90:
            raise ValueError('Scene title missing or too long')
        kind = KINDS[profile][index] if profile != 'news' else {'cards': 'flow'}.get(scene.get('kind'), scene.get('kind', 'network'))
        if kind not in set(KINDS[profile]):
            raise ValueError('Unsupported diagram for this profile')
        scene.update(kind=kind, punchline=cue, effect='none',
                     labels=scene.get('labels', [])[:2])
    plan.update(profile=profile, series=BRANDS[profile],
                narration=' '.join(s['narration'] for s in scenes))
    return plan


def prepare(profile):
    if profile == 'news':
        # Keep the existing fresh-official-source and factual-review gates.
        from news.editor import prepare as news_prepare
        plan = news_prepare()
        if plan is None:
            raise RuntimeError('No fresh official news; no invented news sample')
        for scene in plan['scenes']:
            scene['cue'] = scene['punchline']
        return validate(plan, profile)
    from film_factory.editor import ask
    brief = BRIEFS[profile]
    schema = {'type': 'OBJECT', 'properties': {'title': {'type': 'STRING'}, 'scenes': {
        'type': 'ARRAY', 'minItems': 6, 'maxItems': 6, 'items': {'type': 'OBJECT', 'properties': {
            'title': {'type': 'STRING'}, 'narration': {'type': 'STRING'},
            'cue': {'type': 'STRING'}, 'labels': {'type': 'ARRAY', 'items': {'type': 'STRING'}}},
            'required': ['title', 'narration', 'cue', 'labels']}}}, 'required': ['title', 'scenes']}
    prompt = ('Write six scenes in conversational Egyptian Arabic. Each scene explains the corresponding numbered fact, in order; '
              '35–45 space-separated spoken words per scene. Hook, explanation, payoff. No greetings or calls to subscribe. '
              'Only supplied facts; no new dates, statistics, quotations, witnesses or claims of independent source verification. '
              'No digits in spoken narration. title is a short Arabic scene heading. cue is 2–5 consecutive narration words. '
              'labels are up to two short terms actually spoken. These will be original explanatory diagrams, not photographs. '
              'For horror use a sober tense documentary voice, no fabricated victims, supernatural cause or screams. DATA: ')
    draft = ask(prompt + json.dumps(brief, ensure_ascii=False), schema=schema)
    plan = validate(draft, profile)
    review = ask('Check every sentence ONLY against supplied facts, including dates and causal uncertainty. '
                 'Reject invented details. Return supported and issues. DATA: ' +
                 json.dumps({'brief': brief, 'scenes': plan['scenes']}, ensure_ascii=False), review=True)
    if review.get('supported') is not True or review.get('issues'):
        raise ValueError('Editorial review rejected the motion script')
    plan.update(source={'publisher': brief['publisher'], 'url': brief['url']},
                editorial_review=review, topic_id='motion-' + profile + '-v1',
                documented=True, fiction=False)
    return plan


def preview_plan(profile):
    """Explicitly silent storyboard, never represented as a finished narrated film."""
    headings = {
        'science': ['جلد الأخطبوط', 'أكياس الصبغة', 'إشارات الأعصاب', 'طبقات الجلد', 'تمويه وتواصل', 'تغيير الشكل لحظة بلحظة'],
        'history': ['قناة السويس', 'طريق أقصر', 'سنين الحفر', 'افتتاح القناة', 'محطات في التاريخ', 'ممر بين بحرين'],
        'horror': ['بحيرة نيوس', 'تراكم في الأعماق', 'غاز غير مرئي', 'الوديان المنخفضة', 'تنفيس تدريجي', 'تفسير علمي لحادثة حقيقية'],
        'news': ['الذكاء الاصطناعي', 'من المدخلات للمعالجة', 'مقارنة الأفكار', 'تدفق البيانات', 'تطورات التقنية', 'شرح بصري للخبر']}
    return {'title': headings[profile][0], 'series': BRANDS[profile], 'profile': profile,
            'source': {'publisher': 'معاينة حركة صامتة ، ليست حلقة نهائية', 'url': ''},
            'scenes': [{'title': title, 'kind': KINDS[profile][i], 'labels': [],
                        'narration': '', 'cue': '', 'effect': 'none'} for i, title in enumerate(headings[profile])]}
