// Run: node finance-app/tests/engine.test.js
'use strict';
const assert = require('assert');
const path = require('path');
const E = require(path.join(__dirname, '..', 'js', 'engine.js'));
const { createSeed } = require(path.join(__dirname, '..', 'js', 'data.js'));

const NOW = new Date('2026-11-08T12:00:00');
let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ✓ ' + name); }
  catch (e) { console.error('  ✗ ' + name + '\n    ' + e.message); process.exitCode = 1; }
}
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, (msg || '') + ` expected ${b}±${tol}, got ${a}`);

function simpleProfile(over) {
  return Object.assign({
    monthlyIncome: 10000000, fixedExpenses: 4000000, variableExpenses: 2000000,
    cash: 20000000, emergencyMonths: 3, savingsReturn: 0, investments: [], debts: [],
  }, over || {});
}
function goal(over) {
  return Object.assign({
    id: 'x', name: 'x', price: 12000000, priceDate: NOW.toISOString(), inflation: 0,
    saved: 0, deadline: E.addMonths(NOW, 12).toISOString(), priority: 'high', rank: 0,
    scenario: 'normal', status: 'active', reachedMilestones: [],
  }, over || {});
}

console.log('profile analysis');
test('seed net worth matches the design (24,850,000)', () => {
  const s = createSeed(NOW);
  assert.strictEqual(E.analyzeProfile(s.profile, s.goals).netWorth, 24850000);
});
test('capacity = surplus minus 20% buffer when emergency fund is complete', () => {
  const a = E.analyzeProfile(simpleProfile(), []);
  assert.strictEqual(a.surplus, 4000000);
  assert.strictEqual(a.emergencyTarget, 18000000);
  assert.strictEqual(a.freeCash, 2000000);
  near(a.capacity, 3200000, 1);
});
test('incomplete emergency fund takes part of the surplus first', () => {
  const a = E.analyzeProfile(simpleProfile({ cash: 6000000 }), []);
  assert.ok(a.emergencyGap === 12000000);
  near(a.emergencyMonthly, Math.min(12000000 / 6, 4000000 * 0.3), 1);
  near(a.capacity, 3200000 - 1200000, 1);
});
test('money already earmarked for goals is not counted as free cash', () => {
  const a = E.analyzeProfile(simpleProfile(), [goal({ saved: 2000000 })]);
  assert.strictEqual(a.freeCash, 0);
});
test('investments are discounted by liquidity and volatility, never 1:1 cash', () => {
  const a = E.analyzeProfile(simpleProfile({ investments: [{ id: 'i', name: 's', type: 'stock', value: 10000000 }] }), []);
  near(a.investUsable, 10000000 * 0.85 * 0.7, 1);
  assert.strictEqual(a.freeCash, 2000000, 'investments must not change free cash');
});
test('debt payments reduce surplus and debt balance reduces net worth', () => {
  const a = E.analyzeProfile(simpleProfile({ debts: [{ id: 'd', monthlyPayment: 1000000, balance: 5000000 }] }), []);
  assert.strictEqual(a.surplus, 3000000);
  assert.strictEqual(a.netWorth, 20000000 - 5000000);
});

console.log('goal math');
test('required monthly with no inflation/return is a straight split', () => {
  near(E.requiredMonthly(goal(), 12, NOW, 0), 1000000, 0.01);
});
test('inflation raises the target and the monthly requirement', () => {
  const g = goal({ inflation: 0.25 });
  near(E.targetAt(g, 12, NOW), 15000000, 1);
  near(E.requiredMonthly(g, 12, NOW, 0), 15000000 / 12, 1);
});
test('savings return lowers the monthly requirement (annuity formula)', () => {
  const r = E.monthlyRate(0.18);
  const pmt = E.requiredMonthly(goal(), 12, NOW, 0.18);
  const fv = pmt * (Math.pow(1 + r, 12) - 1) / r;
  near(fv, 12000000, 1);
  assert.ok(pmt < 1000000);
});
test('an on-plan goal is reached exactly at its deadline', () => {
  const g = goal({ inflation: 0.2 });
  const P = E.planAll(simpleProfile({ savingsReturn: 0.1 }), [g], NOW);
  assert.strictEqual(P.plans.x.projectedMonths, 12);
  assert.strictEqual(P.plans.x.feasibility, 'onTrack');
});
test('fast track is never slower than normal, conservative never faster', () => {
  const s = createSeed(NOW);
  const P = E.planAll(s.profile, s.goals, NOW);
  for (const id of Object.keys(P.plans)) {
    const sc = P.plans[id].scenarios;
    assert.ok(sc.fast.months <= sc.normal.months, id + ' fast');
    assert.ok(sc.conservative.months >= sc.normal.months, id + ' conservative');
  }
});
test('fast track never plans more than 95% of the real surplus', () => {
  const s = createSeed(NOW);
  const P = E.planAll(s.profile, s.goals, NOW);
  for (const id of Object.keys(P.plans)) {
    const others = P.totalAllocated - P.plans[id].allocated;
    assert.ok(P.plans[id].scenarios.fast.monthly + others <= P.analysis.surplus * 0.95 + 1, id);
  }
});
test('allocation respects priority order and never exceeds capacity', () => {
  const goals = [goal({ id: 'a', rank: 0 }), goal({ id: 'b', rank: 1, priority: 'low' })];
  const { alloc, free } = E.allocate(1500000, goals, [1000000, 1000000]);
  near(alloc[0], 1000000, 1);
  assert.ok(alloc[1] > 0 && alloc[1] < 1000000);
  near(alloc[0] + alloc[1] + free, 1500000, 1);
});
test('capacity freed by a finished goal cascades to the next one', () => {
  const p = simpleProfile();
  const goals = [goal({ id: 'a', price: 6000000, deadline: E.addMonths(NOW, 3).toISOString() }),
                 goal({ id: 'b', rank: 1, price: 60000000, deadline: E.addMonths(NOW, 12).toISOString() })];
  const sim = E.simulatePortfolio(p, goals, NOW);
  const m = sim.results.b.monthly;
  assert.ok(m[5] > m[0] * 1.2, 'goal b should get more after goal a is done');
});
test('unreachable when price grows faster than savings', () => {
  const p = simpleProfile({ monthlyIncome: 6100000 });
  const P = E.planAll(p, [goal({ price: 500000000, inflation: 0.4 })], NOW);
  assert.strictEqual(P.plans.x.projectedMonths, Infinity);
  assert.strictEqual(P.plans.x.feasibility, 'unrealistic');
});
test('no surplus → impossible', () => {
  const P = E.planAll(simpleProfile({ monthlyIncome: 5000000 }), [goal()], NOW);
  assert.strictEqual(P.plans.x.feasibility, 'impossible');
});

console.log('what-if, roadmap, schedule');
test('saving 2M more per month brings the date forward', () => {
  const s = createSeed(NOW);
  const w = E.whatIf(s.profile, s.goals, 'g1', NOW, { extraMonthly: 2000000 });
  assert.ok(w.after < w.before && w.saved > 0);
});
test('milestones are 10/25/50/75/100 with non-decreasing dates', () => {
  const s = createSeed(NOW);
  const ms = E.planAll(s.profile, s.goals, NOW).plans.g1.milestones;
  assert.deepStrictEqual(ms.map((m) => m.pct), [10, 25, 50, 75, 100]);
  for (let i = 1; i < ms.length; i++) assert.ok(ms[i].date >= ms[i - 1].date);
  assert.strictEqual(ms.filter((m) => m.status === 'current').length, 1);
});
test('behind-schedule detection uses the agreed baseline', () => {
  const s = createSeed(NOW);
  const st = E.scheduleStatus(s.goals[0], NOW);
  assert.ok(st.behind);
  assert.strictEqual(st.expected, 200000 + 800000 * 3);
});
test('profile change produces explained diffs without touching goal fields', () => {
  const s = createSeed(NOW);
  const before = E.planAll(s.profile, s.goals, NOW);
  const snapshot = JSON.stringify(s.goals);
  const p2 = Object.assign({}, s.profile, { monthlyIncome: s.profile.monthlyIncome + 1000000 });
  const after = E.planAll(p2, s.goals, NOW);
  const reasons = E.profileChangeReasons(s.profile, p2);
  const diff = E.diffPlans(before, after, reasons);
  assert.deepStrictEqual(reasons, [{ key: 'income', delta: 1000000 }]);
  assert.ok(Object.keys(diff).length > 0);
  assert.strictEqual(JSON.stringify(s.goals), snapshot, 'goals must not change silently');
});

console.log('gamification');
test('levels', () => {
  assert.strictEqual(E.levelFromXp(0).level, 1);
  assert.strictEqual(E.levelFromXp(150).level, 2);
  assert.strictEqual(E.levelFromXp(1399).level, 4);
});
test('streak counts consecutive weeks, tolerating an empty current week', () => {
  const d = (days) => ({ date: new Date(NOW.getTime() - days * 864e5).toISOString() });
  assert.strictEqual(E.computeStreak([d(7), d(14), d(21)], NOW), 3);
  assert.strictEqual(E.computeStreak([d(7), d(21)], NOW), 1);
});
test('deposit XP rewards consistency, not amount', () => {
  const a = createSeed(NOW), b = createSeed(NOW);
  const small = E.applyDeposit(a, 'g3', 100000, NOW);
  const big = E.applyDeposit(b, 'g3', 900000, NOW);
  assert.strictEqual(small.xp, big.xp - (big.milestones.reduce((s, m) => s + m.xp, 0)));
  const again = E.applyDeposit(a, 'g3', 100000, NOW);
  assert.strictEqual(again.xp, 0, 'second deposit in the same week earns no extra XP');
});
test('deposit crossing a milestone awards it once', () => {
  const s = createSeed(NOW);
  const ev = E.applyDeposit(s, 'g2', 1000000, NOW);
  assert.ok(ev.milestones.some((m) => m.pct === 25));
  const ev2 = E.applyDeposit(s, 'g2', 1000, NOW);
  assert.ok(!ev2.milestones.some((m) => m.pct === 25));
});
test('over-saving warns instead of rewarding', () => {
  const s = createSeed(NOW);
  const ev = E.applyDeposit(s, 'g1', 5000000, NOW);
  assert.ok(ev.warnings.length > 0);
  assert.ok(ev.badges.indexOf('safe_saver') === -1);
});
test('reaching the full (inflated) price completes the goal', () => {
  const s = createSeed(NOW);
  const ev = E.applyDeposit(s, 'g2', 4000000, NOW);
  assert.ok(ev.completed);
  assert.strictEqual(s.goals.find((g) => g.id === 'g2').status, 'completed');
});

console.log(`\n${passed} passed${process.exitCode ? ', some FAILED' : ''}`);
