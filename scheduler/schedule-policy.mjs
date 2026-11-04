export function normalizePolicy(config) {
  const trial = config.publication_time_trial || {};
  const policy = {timezone: config.timezone, baseline: {productionHour: config.production_local_hour, publicationHour: config.publication_local_hour, dayOffset: config.publication_day_offset || 0}, trial: {enabled: trial.enabled === true, start: trial.start_date || '0000-01-01', end: trial.end_date_exclusive || '0000-01-01', productionHour: trial.production_local_hour ?? 19, publicationHour: trial.publication_local_hour ?? 12, dayOffset: trial.production_day_offset ?? -1}};
  validatePolicy(policy); return policy;
}
export function validatePolicy(policy) {
  if (policy.timezone !== 'Africa/Cairo') throw new Error('Only the configured Cairo clock is allowed');
  for (const plan of [policy.baseline, policy.trial]) {
    if (![plan.productionHour, plan.publicationHour].every(hour => Number.isInteger(hour) && hour >= 0 && hour <= 23) || ![0, -1].includes(plan.dayOffset)) throw new Error('Invalid release clock policy');
  }
  if (policy.trial.enabled && (!/^\d{4}-\d{2}-\d{2}$/.test(policy.trial.start) || !/^\d{4}-\d{2}-\d{2}$/.test(policy.trial.end) || policy.trial.start >= policy.trial.end)) throw new Error('Invalid trial date range');
  return policy;
}
export const DEFAULT_POLICY = normalizePolicy({timezone:'Africa/Cairo',production_local_hour:9,publication_local_hour:17,publication_day_offset:0,publication_time_trial:{enabled:true,start_date:'2026-11-04',end_date_exclusive:'2026-11-18',production_local_hour:19,publication_local_hour:12,production_day_offset:-1}});
export function shiftDay(day, count) { return new Date(Date.parse(day + 'T12:00:00Z') + count * 86400000).toISOString().slice(0,10); }
export function releasePlan(day, policy = DEFAULT_POLICY) {
  validatePolicy(policy);
  const plan = policy.trial.enabled && day >= policy.trial.start && day < policy.trial.end ? policy.trial : policy.baseline;
  return {...plan, preparationDay: shiftDay(day, plan.dayOffset)};
}
export function policyFromEnv(env) { return env.SCHEDULE_POLICY ? validatePolicy(JSON.parse(env.SCHEDULE_POLICY)) : DEFAULT_POLICY; }
export function cronExpressions(policy) {
  const plans = [policy.baseline, ...(policy.trial.enabled ? [policy.trial] : [])];
  const hours = key => [...new Set(plans.flatMap(p => [2,3].map(offset => (p[key] - offset + 24) % 24)))].sort((a,b) => a-b).join(',');
  return [`0,17 ${hours('productionHour')} * * *`, `35 ${hours('publicationHour')} * * *`];
}
