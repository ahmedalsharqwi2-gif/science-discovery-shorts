// director/storyboard.mjs - turns an episode's scenes into a visual script
// (storyboard.json) before render: one idea per scene, template choice by
// information type, no template twice in a row, keyword emphasis, transition
// plan. Deterministic and auditable (owner pro-motion spec, section 5).
const TEMPLATE_BY_KIND = {
  phenomenon: 'technical-illustration',
  cause: 'flow-diagram',
  journey: 'map-or-timeline',
  comparison: 'comparison',
  stat: 'big-number',
  quote: 'quote-card',
  intro: 'animated-title',
  outro: 'endcard-cta',
};
const FALLBACK_CYCLE = ['technical-illustration', 'caption-callout', 'comparison', 'flow-diagram'];
const TRANSITIONS = ['morph', 'zoom-through', 'mask-reveal', 'wipe-shape'];

export function buildStoryboard(episode, {transitions = TRANSITIONS} = {}) {
  const scenes = episode.scenes.map((s, i) => {
    let template = TEMPLATE_BY_KIND[s.template] || TEMPLATE_BY_KIND[s.kind] || 'technical-illustration';
    return {index: i, template, keyword: s.keyword || null, emphasis: [...new Set([s.keyword, ...(s.labels || [])].filter(Boolean))], text: s.text};
  });
  // no template twice in a row: swap to the next fallback not equal to neighbours
  for (let i = 1; i < scenes.length; i++) {
    if (scenes[i].template === scenes[i - 1].template) {
      const alt = FALLBACK_CYCLE.find(t => t !== scenes[i - 1].template && t !== scenes[i + 1]?.template);
      scenes[i] = {...scenes[i], template: alt, swappedFrom: scenes[i].template};
    }
  }
  const planned = scenes.map((s, i) => ({...s, transitionIn: i === 0 ? null : transitions[i % transitions.length]}));
  return {
    schema: 1, title: episode.title, scenes: planned,
    rules: {oneIdeaPerScene: true, noTemplateRepeatAdjacent: true, visualChangeEverySeconds: [2, 4], hookInFirstSeconds: 3},
    generatedAt: new Date().toISOString(),
  };
}

export function validateStoryboard(sb) {
  const problems = [];
  for (let i = 1; i < sb.scenes.length; i++) {
    if (sb.scenes[i].template === sb.scenes[i - 1].template) problems.push('template repeats at scene ' + i);
  }
  if (!sb.scenes.length) problems.push('empty storyboard');
  return problems;
}
