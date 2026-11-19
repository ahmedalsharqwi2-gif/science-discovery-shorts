// Thin adapter: niche_intel modules call client.call({name,system,user,schema});
// this maps it onto the pipeline's pooled Gemini client (keys, cooldowns, rate
// limits, model pinning all stay in pipeline/gemini.mjs). No key => null client.
export async function nicheGemini() {
  const hasKey = ['GEMINI_TEXT_API_KEY', 'GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3'].some(k => process.env[k]);
  if (!hasKey) return null;
  const {provider} = await import('../pipeline/provider-client.mjs');
  const client = await provider();
  return {
    async call({name, system, user, schema, maxOutputTokens = 4096}) {
      try {
        const res = await client.generate('text', {
          systemInstruction: {parts: [{text: system}]},
          contents: [{parts: [{text: user}]}],
          generationConfig: {responseMimeType: 'application/json', temperature: 0.4, maxOutputTokens},
        }, {settings: {task: 'niche_' + name, schema: 1}, useCache: true});
        const text = res.candidates[0].content.parts.filter(p => p.text).map(p => p.text).join('');
        return {ok: true, data: JSON.parse(text), model: res._pipeline?.model};
      } catch (e) { return {ok: false, reason: String(e.code || e.message).slice(0, 80)}; }
    },
  };
}
