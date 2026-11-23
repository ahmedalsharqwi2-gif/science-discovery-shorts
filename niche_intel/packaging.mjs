// niche_intel/packaging.mjs - per-video packaging: 3 candidate titles, a
// 3-second hook, CTA, keyworded description, hashtags, AI-content disclosure,
// and an automated title-promise-vs-script check. Honest titles only: no
// clickbait the video does not pay off (owner rule 5).

// Deterministic title picker: reasonable length, contains the keyword, no
// duplication against recent titles, no ALL-CAPS/misleading markers.
export function pickTitle(candidates, {primaryKeyword, recentTitles = []} = {}) {
  const seen = new Set(recentTitles.map(t => t.trim()));
  const scored = candidates.filter(t => t && !seen.has(t.trim())).map(t => {
    let s = 0;
    const len = [...t].length;
    if (len >= 25 && len <= 70) s += 2; else if (len < 90) s += 1;
    if (primaryKeyword && t.includes(primaryKeyword)) s += 2;
    if (!/!{2,}|صدمة|لن تصدق/.test(t)) s += 1; // honest curiosity, not bait
    return {t, s};
  }).sort((a, b) => b.s - a.s);
  return scored[0]?.t || null;
}

// Title-promise test: the script must cover what the title promises. Uses the
// episode script segments when available (post-production run) or the topic
// description otherwise. Keyword from the title must appear in the content.
export function titlePromiseCheck(title, {primaryKeyword, scriptSegments = [], topicDescription = ''} = {}) {
  const content = (scriptSegments.map(s => s.text || s).join(' ') || topicDescription).trim();
  if (!content) return {ok: false, reason: 'no script/description to check against'};
  const kw = primaryKeyword && title.includes(primaryKeyword) ? primaryKeyword
    : title.replace(/[؟?!.]/g, '').split(/\s+/).filter(w => w.length > 3).sort((a, b) => b.length - a.length)[0];
  return content.includes(kw)
    ? {ok: true, keyword: kw}
    : {ok: false, keyword: kw, reason: 'title keyword not covered by content'};
}

export function buildPackaging({topic, titles, hook, cta, description, hashtags, aiDisclosure, scriptSegments = []}) {
  const chosen = pickTitle(titles, {primaryKeyword: topic.primaryKeyword});
  const promise = chosen ? titlePromiseCheck(chosen, {primaryKeyword: topic.primaryKeyword, scriptSegments, topicDescription: topic.description || ''}) : {ok: false, reason: 'no title survived filters'};
  return {
    topic: topic.title, keyword: topic.primaryKeyword,
    titles: {candidates: titles, chosen},
    hook, cta, description, hashtags,
    aiDisclosure, // see docs/PLATFORM_POLICY.md
    titlePromiseCheck: promise,
    generatedAt: new Date().toISOString(),
  };
}

// Gemini copy generator. On failure the caller marks packaging
// status: 'failed' rather than shipping template text as if it were copy.
export async function generatePackaging(topic, profile, geminiClient, opts = {}) {
  if (!geminiClient) return {ok: false, reason: 'no_gemini'};
  const r = await geminiClient.call({
    name: 'packaging', stage: 'niche-intel', maxOutputTokens: 4096,
    system: 'You write honest Arabic YouTube Shorts packaging for the channel tone below. Curiosity allowed only when the video pays it off. JSON only.\nTone: ' + (profile.tone || ''),
    user: 'Topic: ' + topic.title + '\nKeyword: ' + topic.primaryKeyword + '\nIntent: ' + (topic.searchIntent || '') +
      '\nReturn {"titles": ["3 Arabic titles, each containing the keyword naturally"], "hook": "<first-3-seconds spoken line>", "cta": "<closing line>", "description": "<2-3 lines with keywords naturally>", "hashtags": ["3-5"]}.',
    schema: {type: 'OBJECT', properties: {titles: {type: 'ARRAY', items: {type: 'STRING'}}, hook: {type: 'STRING'}, cta: {type: 'STRING'}, description: {type: 'STRING'}, hashtags: {type: 'ARRAY', items: {type: 'STRING'}}}, required: ['titles', 'hook', 'cta', 'description', 'hashtags']},
  });
  if (!r.ok) return {ok: false, reason: r.reason};
  const disclosure = profile.aiDisclosure ?? 'محتوى مُنشأ بمساعدة الذكاء الاصطناعي';
  return {ok: true, packaging: buildPackaging({topic, ...r.data, aiDisclosure: disclosure, scriptSegments: opts.scriptSegments})};
}
