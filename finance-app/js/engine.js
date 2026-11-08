/*
 * Smart Financial Goals — calculation engine
 * ------------------------------------------
 * Pure functions, no DOM. Works in the browser (window.FinEngine) and in Node (require).
 *
 * All money values are integers in Toman. All rates are annual decimals (0.25 = 25%).
 * Time is modelled in whole months; month 0 is "now".
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.FinEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Constants                                                          */
  /* ------------------------------------------------------------------ */

  const MAX_MONTHS = 600;              // 50 years: beyond this a goal is "unreachable"
  const SAFETY_BUFFER = 0.2;           // 20% of monthly surplus is never planned (irregular costs)
  const RESERVE_SHARE = 0.15;          // 15% of capacity is spread over all goals so none stalls
  const EMERGENCY_REBUILD_SHARE = 0.3; // max share of surplus used to rebuild the emergency fund
  const EMERGENCY_REBUILD_MONTHS = 6;  // target time to rebuild a missing emergency fund

  const PRIORITY_WEIGHT = { high: 3, medium: 2, low: 1 };

  // How much of an asset's value can be turned into cash quickly (liquidity)
  // and how much we discount it for price swings before counting it (volatility haircut).
  const ASSET_RULES = {
    deposit:    { liquidity: 0.95, volatility: 0.00, label: 'سپرده بانکی' },
    fund:       { liquidity: 0.90, volatility: 0.20, label: 'صندوق سرمایه‌گذاری' },
    stock:      { liquidity: 0.85, volatility: 0.30, label: 'سهام' },
    gold:       { liquidity: 0.90, volatility: 0.15, label: 'طلا و ارز' },
    crypto:     { liquidity: 0.85, volatility: 0.50, label: 'رمزارز' },
    realestate: { liquidity: 0.20, volatility: 0.10, label: 'ملک' },
    other:      { liquidity: 0.50, volatility: 0.25, label: 'سایر' },
  };

  const SCENARIOS = {
    conservative: { factor: 0.75, label: 'محافظه‌کارانه', en: 'Conservative' },
    normal:       { factor: 1.00, label: 'متعادل',         en: 'Normal' },
    fast:         { factor: 1.35, label: 'مسیر سریع',      en: 'Fast Track' },
  };

  const MILESTONES = [
    { pct: 10,  xp: 50,  badge: null,          title: 'شروع قدرتمند' },
    { pct: 25,  xp: 100, badge: 'quarter',     title: 'یک‌چهارم مسیر' },
    { pct: 50,  xp: 200, badge: 'halfway',     title: 'نیمه راه' },
    { pct: 75,  xp: 300, badge: null,          title: 'خط پایان در دید' },
    { pct: 100, xp: 500, badge: 'goal_done',   title: 'رسیدی! وقت خرید' },
  ];

  const FEASIBILITY = {
    done:         { label: 'تکمیل شده',          tone: 'mint',  score: 5 },
    comfortable:  { label: 'راحت',               tone: 'mint',  score: 4 },
    onTrack:      { label: 'واقع‌بینانه',         tone: 'mint',  score: 3 },
    challenging:  { label: 'چالشی',              tone: 'amber', score: 2 },
    risky:        { label: 'پرفشار',             tone: 'coral', score: 1 },
    unrealistic:  { label: 'غیرواقع‌بینانه',      tone: 'coral', score: 0 },
    impossible:   { label: 'نیاز به بازنگری',    tone: 'coral', score: 0 },
  };

  const LEVELS = [
    { xp: 0,    name: 'تازه‌کار' },
    { xp: 150,  name: 'پس‌اندازگر' },
    { xp: 400,  name: 'برنامه‌ریز' },
    { xp: 800,  name: 'هدف‌گیر' },
    { xp: 1400, name: 'استراتژیست' },
    { xp: 2200, name: 'مدیر مالی' },
    { xp: 3200, name: 'سرمایه‌ساز' },
    { xp: 4500, name: 'استاد مالی' },
    { xp: 6000, name: 'افسانه' },
  ];

  const BADGES = {
    first_goal:    { icon: '🎯', title: 'اولین قدم',          desc: 'اولین هدف مالی‌ات را ساختی' },
    first_deposit: { icon: '🪙', title: 'شروع پس‌انداز',       desc: 'اولین واریز به یک هدف' },
    quarter:       { icon: '🌱', title: 'یک‌چهارم راه',        desc: 'به ۲۵٪ یک هدف رسیدی' },
    halfway:       { icon: '⚡', title: 'نیمه راه',            desc: 'به ۵۰٪ یک هدف رسیدی' },
    goal_done:     { icon: '🏆', title: 'رسیدم!',              desc: 'یک هدف را کامل کردی' },
    streak_4:      { icon: '🔥', title: '۴ هفته پیوسته',       desc: '۴ هفته پشت سر هم پس‌انداز' },
    streak_12:     { icon: '💎', title: 'ثبات واقعی',          desc: '۱۲ هفته پشت سر هم پس‌انداز' },
    safe_saver:    { icon: '🛡️', title: 'پس‌انداز مسئولانه',   desc: 'پس‌انداز بدون دست زدن به صندوق اضطراری' },
    multi_goal:    { icon: '🧭', title: 'چندهدفه',             desc: '۳ هدف فعال هم‌زمان' },
    planner:       { icon: '🗺️', title: 'برنامه‌ریز',          desc: 'یک سناریو یا برنامه‌ی جدید را انتخاب کردی' },
    level_5:       { icon: '👑', title: 'سطح ۵',               desc: 'به سطح استراتژیست رسیدی' },
  };

  /* ------------------------------------------------------------------ */
  /* Small helpers                                                      */
  /* ------------------------------------------------------------------ */

  const sum = (arr) => arr.reduce((a, b) => a + (Number(b) || 0), 0);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const monthlyRate = (annual) => Math.pow(1 + (Number(annual) || 0), 1 / 12) - 1;

  function toDate(d) { return d instanceof Date ? new Date(d.getTime()) : new Date(d); }

  function addMonths(date, n) {
    const d = toDate(date);
    const day = d.getDate();
    d.setDate(1);
    d.setMonth(d.getMonth() + n);
    const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
    d.setDate(Math.min(day, last));
    return d;
  }

  /** Whole calendar months from a to b (negative if b is before a). */
  function monthsBetween(a, b) {
    const x = toDate(a), y = toDate(b);
    let m = (y.getFullYear() - x.getFullYear()) * 12 + (y.getMonth() - x.getMonth());
    if (y.getDate() < x.getDate()) m -= 1;
    return m;
  }

  /** Price of the goal `t` months from now, grown by its annual price inflation since priceDate. */
  function targetAt(goal, t, now) {
    const g = monthlyRate(goal.inflation);
    const since = goal.priceDate ? Math.max(0, monthsBetween(goal.priceDate, now)) : 0;
    return goal.price * Math.pow(1 + g, since + t);
  }

  /* ------------------------------------------------------------------ */
  /* 1. Profile analysis                                                */
  /* ------------------------------------------------------------------ */

  function analyzeProfile(profile, goals) {
    const p = profile;
    const activeGoals = (goals || []).filter((g) => g.status !== 'completed');
    const debtPayments = sum((p.debts || []).map((d) => d.monthlyPayment));
    const debtBalance = sum((p.debts || []).map((d) => d.balance));
    const expenses = (p.fixedExpenses || 0) + (p.variableExpenses || 0);
    const outflow = expenses + debtPayments;
    const surplus = (p.monthlyIncome || 0) - outflow;

    // Cash that is already earmarked for goals is not available for anything else.
    const earmarked = sum(activeGoals.map((g) => g.saved));
    const emergencyTarget = outflow * (p.emergencyMonths || 0);
    const cashAfterGoals = (p.cash || 0) - earmarked;
    const emergencyHeld = clamp(cashAfterGoals, 0, emergencyTarget);
    const emergencyGap = Math.max(0, emergencyTarget - emergencyHeld);
    const freeCash = Math.max(0, cashAfterGoals - emergencyTarget);

    // If the emergency fund is incomplete, part of the surplus rebuilds it first.
    const emergencyMonthly = emergencyGap > 0
      ? Math.min(emergencyGap / EMERGENCY_REBUILD_MONTHS, Math.max(0, surplus) * EMERGENCY_REBUILD_SHARE)
      : 0;

    // Sustainable monthly capacity for goals: surplus minus safety buffer minus emergency rebuild.
    const capacity = Math.max(0, Math.max(0, surplus) * (1 - SAFETY_BUFFER) - emergencyMonthly);

    // Investments are NOT cash: discount them by liquidity and volatility.
    const investments = (p.investments || []).map((inv) => {
      const rule = ASSET_RULES[inv.type] || ASSET_RULES.other;
      const usable = inv.value * rule.liquidity * (1 - rule.volatility);
      return Object.assign({}, inv, { liquidity: rule.liquidity, volatility: rule.volatility, usable: Math.round(usable) });
    });
    const investTotal = sum(investments.map((i) => i.value));
    const investUsable = sum(investments.map((i) => i.usable));

    const netWorth = (p.cash || 0) + investTotal - debtBalance;
    const savingsRate = p.monthlyIncome > 0 ? surplus / p.monthlyIncome : 0;

    return {
      income: p.monthlyIncome || 0,
      expenses, debtPayments, debtBalance, outflow, surplus, savingsRate,
      earmarked, emergencyTarget, emergencyHeld, emergencyGap, emergencyMonthly,
      emergencyRatio: emergencyTarget > 0 ? emergencyHeld / emergencyTarget : 1,
      freeCash, capacity, bufferAmount: Math.max(0, surplus) * SAFETY_BUFFER,
      investments, investTotal, investUsable, netWorth,
    };
  }

  /* ------------------------------------------------------------------ */
  /* 2. Per-goal math                                                   */
  /* ------------------------------------------------------------------ */

  /**
   * Monthly deposit needed so that after n deposits the balance reaches the (inflated) price.
   * Balance grows at savings return r; deposits happen at the end of each month.
   */
  function requiredMonthly(goal, n, now, savingsReturn, balance, elapsed) {
    const bal = balance == null ? goal.saved : balance;
    n = Math.max(1, Math.round(n));
    const r = monthlyRate(savingsReturn);
    const T = targetAt(goal, (elapsed || 0) + n, now); // price at the deadline month
    const S = bal * Math.pow(1 + r, n);
    if (S >= T) return 0;
    const factor = r > 0 ? (Math.pow(1 + r, n) - 1) / r : n;
    return (T - S) / factor;
  }

  /**
   * Split monthly capacity across active goals.
   *  - 15% of capacity is spread by weight so no goal stalls completely;
   *  - the rest funds goals in the user's priority order, each up to its demand;
   *  - anything left after all demands are met stays as "free capacity".
   * `goals` must already be in rank order; demands[i] is goal i's required monthly.
   */
  function allocate(capacity, goals, demands) {
    const n = goals.length;
    const alloc = new Array(n).fill(0);
    if (!n || capacity <= 0) return { alloc, free: Math.max(0, capacity) };
    const weights = goals.map((g, i) => (PRIORITY_WEIGHT[g.priority] || 1) + (n - i) * 0.25);
    const wSum = sum(weights);

    const reserve = capacity * RESERVE_SHARE;
    for (let i = 0; i < n; i++) alloc[i] = Math.min(demands[i], reserve * weights[i] / wSum);
    let left = capacity - sum(alloc);

    for (let i = 0; i < n && left > 0; i++) {
      const need = Math.max(0, demands[i] - alloc[i]);
      const give = Math.min(need, left);
      alloc[i] += give;
      left -= give;
    }
    return { alloc, free: Math.max(0, left) };
  }

  function rankGoals(goals) {
    return goals.filter((g) => g.status !== 'completed').slice().sort((a, b) => (a.rank || 0) - (b.rank || 0));
  }

  /**
   * Month-by-month simulation of all active goals together. Capacity freed by a finished goal
   * automatically flows to the remaining goals (cascade), which is what really happens.
   *
   * opts.focusId      goal whose contribution is modified
   * opts.factor       multiplier on the focus goal's allocation (scenarios)
   * opts.extraMonthly extra money per month for the focus goal (what-if, outside capacity)
   * opts.lumpSum      one-off amount added to the focus goal at month 0
   */
  function simulatePortfolio(profile, goals, now, opts) {
    opts = opts || {};
    const analysis = analyzeProfile(profile, goals);
    const ranked = rankGoals(goals);
    const r = monthlyRate(profile.savingsReturn);
    const state = ranked.map((g) => ({
      goal: g,
      balance: g.saved + (g.id === opts.focusId ? (opts.lumpSum || 0) : 0),
      deadline: Math.max(1, monthsBetween(now, g.deadline)),
      reachedAt: null,
      series: [],
      monthly: [],
    }));
    const capacity = analysis.capacity;

    for (let t = 0; t <= MAX_MONTHS; t++) {
      // 1. check who has reached their (inflated) target at the start of month t
      for (const s of state) {
        if (s.reachedAt != null) continue;
        s.series.push(s.balance);
        if (s.balance >= targetAt(s.goal, t, now) - 0.5) s.reachedAt = t;
      }
      const active = state.filter((s) => s.reachedAt == null);
      if (!active.length || t === MAX_MONTHS) break;

      // 2. allocate this month's capacity on current demands
      // after the deadline the whole remaining gap is due next month (n = 1)
      const demands = active.map((s) => requiredMonthly(s.goal, Math.max(1, s.deadline - t), now, profile.savingsReturn, s.balance, t));
      const { alloc } = allocate(capacity, active.map((s) => s.goal), demands);

      // 3. deposit
      active.forEach((s, i) => {
        let m = alloc[i];
        if (s.goal.id === opts.focusId) {
          // A scenario is a steady commitment: being ahead of plan must not shrink the deposit,
          // otherwise "fast" or "+2M per month" would silently throttle back to the deadline pace.
          if (s.base == null) s.base = alloc[i];
          m = Math.max(alloc[i], s.base) * (opts.factor == null ? 1 : opts.factor) + (opts.extraMonthly || 0);
        }
        s.monthly.push(m);
        s.balance = s.balance * (1 + r) + m;
      });
    }

    const out = {};
    for (const s of state) {
      out[s.goal.id] = {
        months: s.reachedAt == null ? Infinity : s.reachedAt,
        series: s.series,
        monthly: s.monthly,
        firstMonthly: s.monthly.length ? s.monthly[0] : 0,
      };
    }
    return { analysis, results: out, ranked };
  }

  function pressureOf(monthly, analysis) {
    const ofIncome = analysis.income > 0 ? monthly / analysis.income : 1;
    const ofSurplus = analysis.surplus > 0 ? monthly / analysis.surplus : 1;
    let level = 'low', label = 'کم';
    if (ofIncome > 0.3 || ofSurplus > 0.8) { level = 'high'; label = 'زیاد'; }
    else if (ofIncome > 0.15 || ofSurplus > 0.5) { level = 'medium'; label = 'متوسط'; }
    return { ofIncome, ofSurplus, level, label };
  }

  function classifyFeasibility(goal, req, alloc, analysis, progress) {
    if (progress >= 1) return 'done';
    if (analysis.surplus <= 0) return 'impossible';
    if (req <= alloc * 1.001 + 1) return req / analysis.surplus <= 0.25 ? 'comfortable' : 'onTrack';
    if (req <= analysis.capacity) return 'challenging';
    if (req <= analysis.surplus) return 'risky';
    return 'unrealistic';
  }

  /* ------------------------------------------------------------------ */
  /* 3. Full plan for all goals                                         */
  /* ------------------------------------------------------------------ */

  function planAll(profile, goals, now, overrides) {
    now = toDate(now || new Date());
    overrides = overrides || {};
    const base = simulatePortfolio(profile, goals, now);
    const analysis = base.analysis;
    const ranked = base.ranked;

    // Current-month allocation (for display + feasibility)
    const demands = ranked.map((g) => requiredMonthly(g, Math.max(1, monthsBetween(now, g.deadline)), now, profile.savingsReturn));
    const { alloc, free } = allocate(analysis.capacity, ranked, demands);
    const totalAllocated = sum(alloc);

    const plans = {};
    ranked.forEach((goal, i) => {
      const monthsLeft = Math.max(1, monthsBetween(now, goal.deadline));
      const req = demands[i];
      const allocated = alloc[i];

      // Scenarios: change only this goal's contribution. Fast track may use the buffer, never more.
      const headroom = Math.max(0, analysis.surplus * 0.95 - totalAllocated);
      const scenarios = {};
      for (const key of Object.keys(SCENARIOS)) {
        let factor = SCENARIOS[key].factor;
        if (key === 'fast' && allocated > 0) factor = Math.min(factor, 1 + headroom / allocated);
        const sim = key === 'normal' ? base : simulatePortfolio(profile, goals, now, { focusId: goal.id, factor });
        const res = sim.results[goal.id];
        const monthly = allocated * factor;
        scenarios[key] = {
          key, label: SCENARIOS[key].label, en: SCENARIOS[key].en,
          monthly, months: res.months,
          date: isFinite(res.months) ? addMonths(now, res.months) : null,
          pressure: pressureOf(monthly, analysis),
          meetsDeadline: res.months <= monthsLeft,
          series: res.series, monthlyPath: res.monthly,
        };
      }

      const selectedKey = overrides[goal.id] || goal.scenario || 'normal';
      const sel = scenarios[selectedKey] || scenarios.normal;
      const projectedTarget = isFinite(sel.months) ? targetAt(goal, sel.months, now) : targetAt(goal, monthsLeft, now);
      const progress = clamp(goal.saved / projectedTarget, 0, 1);
      const feasibility = classifyFeasibility(goal, req, allocated, analysis, goal.saved >= targetAt(goal, 0, now) ? 1 : 0);

      // Capacity released later by other goals (cascade) — explain it to the user.
      let cascade = null;
      const path = sel.monthlyPath;
      if (path.length > 1) {
        const later = Math.max.apply(null, path);
        const at = path.findIndex((m) => m > path[0] * 1.2 + 1000);
        if (at > 0) cascade = { fromMonth: at, monthly: later, date: addMonths(now, at) };
      }

      plans[goal.id] = {
        goalId: goal.id,
        rankIndex: i,
        monthsLeft,
        deadlineTarget: targetAt(goal, monthsLeft, now),
        currentTarget: targetAt(goal, 0, now),
        requiredMonthly: req,
        allocated,
        scenarios,
        selected: selectedKey,
        projectedMonths: sel.months,
        projectedDate: sel.date,
        projectedTarget,
        progress,
        feasibility,
        feasibilityInfo: FEASIBILITY[feasibility],
        milestones: buildMilestones(goal, sel, projectedTarget, now),
        cadence: cadenceOf(sel.monthly),
        schedule: scheduleStatus(goal, now),
        cascade,
        advice: adviceFor(goal, req, allocated, sel, monthsLeft, analysis, now),
      };
    });

    return { analysis, plans, ranked, totalAllocated, freeCapacity: free, totalDemand: sum(demands) };
  }

  /* ------------------------------------------------------------------ */
  /* 4. What-if                                                         */
  /* ------------------------------------------------------------------ */

  function whatIf(profile, goals, goalId, now, opts) {
    now = toDate(now || new Date());
    const goal = goals.find((g) => g.id === goalId);
    const baseSim = simulatePortfolio(profile, goals, now, { focusId: goalId, factor: SCENARIOS[goal.scenario || 'normal'].factor });
    const sim = simulatePortfolio(profile, goals, now, {
      focusId: goalId,
      factor: SCENARIOS[goal.scenario || 'normal'].factor,
      extraMonthly: opts.extraMonthly || 0,
      lumpSum: opts.lumpSum || 0,
    });
    const before = baseSim.results[goalId].months;
    const after = sim.results[goalId].months;
    return {
      before, after,
      saved: isFinite(before) && isFinite(after) ? before - after : (isFinite(after) ? Infinity : 0),
      date: isFinite(after) ? addMonths(now, after) : null,
    };
  }

  /* ------------------------------------------------------------------ */
  /* 5. Roadmap                                                         */
  /* ------------------------------------------------------------------ */

  function buildMilestones(goal, scenario, projectedTarget, now) {
    const reached = goal.reachedMilestones || [];
    let currentSet = false;
    return MILESTONES.map((m) => {
      const amount = projectedTarget * m.pct / 100;
      const idx = scenario.series.findIndex((b) => b >= amount - 0.5);
      const done = reached.indexOf(m.pct) !== -1 || goal.saved >= amount - 0.5;
      let status = done ? 'done' : 'upcoming';
      if (!done && !currentSet) { status = 'current'; currentSet = true; }
      return {
        pct: m.pct, title: m.title, amount,
        remaining: Math.max(0, amount - goal.saved),
        date: idx >= 0 ? addMonths(now, idx) : (m.pct === 100 && scenario.date ? scenario.date : null),
        status, xp: m.xp, badge: m.badge,
      };
    });
  }

  function cadenceOf(monthly) {
    return {
      monthly,
      weekly: monthly * 12 / 52,
      daily: monthly * 12 / 365,
    };
  }

  /** Compare actual savings to the plan the user last agreed to. */
  function scheduleStatus(goal, now) {
    const b = goal.baseline;
    if (!b) return { tracked: false };
    const elapsed = Math.max(0, monthsBetween(b.date, now));
    const expected = b.saved + b.monthly * elapsed;
    const gap = expected - goal.saved;
    const tolerance = Math.max(b.monthly * 0.5, 1);
    return {
      tracked: true, elapsed, expected,
      gap: Math.max(0, gap),
      ahead: Math.max(0, -gap),
      behind: gap > tolerance,
      isAhead: -gap > tolerance,
    };
  }

  function adviceFor(goal, req, alloc, sel, monthsLeft, analysis, now) {
    const tips = [];
    if (analysis.emergencyGap > 0) {
      tips.push({ type: 'warn', text: 'صندوق اضطراری کامل نیست؛ بخشی از مازاد ماهانه اول صرف تکمیل آن می‌شود.' });
    }
    if (req > alloc + 1 && isFinite(sel.months)) {
      const extra = Math.max(0, sel.months - monthsLeft);
      tips.push({ type: 'info', kind: 'extend', months: extra, date: addMonths(now, sel.months),
        text: 'برای رسیدن در مهلت فعلی ماهانه ' + Math.round(req - alloc) + ' تومان بیشتر لازم است، یا مهلت را ' + extra + ' ماه تمدید کن.' });
    }
    if (!isFinite(sel.months)) {
      tips.push({ type: 'warn', text: 'با سهم فعلی، رشد قیمت از سرعت پس‌انداز جلو می‌زند. اولویت هدف را بالا ببر یا مبلغ هدف را بازبینی کن.' });
    }
    return tips;
  }

  /* ------------------------------------------------------------------ */
  /* 6. Dynamic roadmap: explain what changed                           */
  /* ------------------------------------------------------------------ */

  function diffPlans(oldPlan, newPlan, reasons) {
    const out = {};
    for (const id of Object.keys(newPlan.plans)) {
      const a = oldPlan.plans[id], b = newPlan.plans[id];
      if (!a) continue;
      const changes = [];
      const am = a.projectedMonths, bm = b.projectedMonths;
      if (am !== bm) {
        if (isFinite(am) && isFinite(bm)) changes.push({ kind: 'time', delta: bm - am, from: a.projectedDate, to: b.projectedDate });
        else changes.push({ kind: 'time', delta: isFinite(bm) ? -Infinity : Infinity, from: a.projectedDate, to: b.projectedDate });
      }
      if (Math.abs(a.allocated - b.allocated) >= 1000) changes.push({ kind: 'monthly', from: a.allocated, to: b.allocated });
      if (a.feasibility !== b.feasibility) changes.push({ kind: 'feasibility', from: a.feasibility, to: b.feasibility });
      if (changes.length) out[id] = { changes, reasons: reasons || [] };
    }
    return out;
  }

  /** Human-readable reasons for a profile change. */
  function profileChangeReasons(oldP, newP) {
    const r = [];
    const d = (k) => (newP[k] || 0) - (oldP[k] || 0);
    if (d('monthlyIncome')) r.push({ key: 'income', delta: d('monthlyIncome') });
    if (d('fixedExpenses') || d('variableExpenses')) r.push({ key: 'expenses', delta: d('fixedExpenses') + d('variableExpenses') });
    if (d('cash')) r.push({ key: 'cash', delta: d('cash') });
    const inv = (p) => sum((p.investments || []).map((i) => i.value));
    if (inv(newP) !== inv(oldP)) r.push({ key: 'investments', delta: inv(newP) - inv(oldP) });
    const debt = (p) => sum((p.debts || []).map((i) => i.monthlyPayment));
    if (debt(newP) !== debt(oldP)) r.push({ key: 'debts', delta: debt(newP) - debt(oldP) });
    if (d('emergencyMonths')) r.push({ key: 'emergency', delta: d('emergencyMonths') });
    if ((newP.savingsReturn || 0) !== (oldP.savingsReturn || 0)) r.push({ key: 'return', delta: d('savingsReturn') });
    return r;
  }

  /* ------------------------------------------------------------------ */
  /* 7. Gamification                                                    */
  /* ------------------------------------------------------------------ */

  function levelFromXp(xp) {
    let i = 0;
    while (i + 1 < LEVELS.length && xp >= LEVELS[i + 1].xp) i++;
    const cur = LEVELS[i], next = LEVELS[i + 1];
    return {
      level: i + 1, name: cur.name, xp,
      floor: cur.xp, next: next ? next.xp : null,
      progress: next ? (xp - cur.xp) / (next.xp - cur.xp) : 1,
    };
  }

  // Weeks start on Saturday (Iranian week). Day 0 = 1970-01-03 was a Saturday.
  function weekIndex(date) {
    const d = toDate(date);
    const utc = Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
    return Math.floor((utc / 86400000 - 2) / 7);
  }

  /** Consecutive weeks with at least one deposit, ending this week (or last week if none yet this week). */
  function computeStreak(deposits, now) {
    const weeks = new Set((deposits || []).map((d) => weekIndex(d.date)));
    let w = weekIndex(now);
    if (!weeks.has(w)) w -= 1;
    let streak = 0;
    while (weeks.has(w)) { streak++; w--; }
    return streak;
  }

  /**
   * Record a deposit and return everything that happened (XP, milestones, badges, warnings).
   * XP rewards consistency, not size: a huge deposit earns the same as a modest one.
   * Mutates `state` (profile, goals, game).
   */
  function applyDeposit(state, goalId, amount, now) {
    now = toDate(now || new Date());
    const events = { xp: 0, milestones: [], badges: [], warnings: [], completed: false, levelUp: null };
    const goal = state.goals.find((g) => g.id === goalId);
    if (!goal || !(amount > 0)) return events;
    const game = state.game;
    const before = planAll(state.profile, state.goals, now);
    const beforeAnalysis = before.analysis;
    const levelBefore = levelFromXp(game.xp).level;

    // Responsible-saving guard: compare this month's goal deposits with the real surplus.
    const thisMonth = game.deposits.filter((d) => {
      const x = toDate(d.date);
      return x.getFullYear() === now.getFullYear() && x.getMonth() === now.getMonth();
    });
    const monthTotal = sum(thisMonth.map((d) => d.amount)) + amount;
    const overSurplus = beforeAnalysis.surplus > 0 && monthTotal > beforeAnalysis.surplus;
    if (overSurplus) {
      events.warnings.push('واریزهای این ماه از مازاد درآمدت بیشتر شده. مطمئن شو هزینه‌های ضروری و صندوق اضطراری آسیب نمی‌بینند.');
    }

    const firstThisWeek = !game.deposits.some((d) => weekIndex(d.date) === weekIndex(now));
    goal.saved += amount;
    state.profile.cash += amount; // new savings land in cash, earmarked for this goal
    game.deposits.push({ id: 'd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), goalId, amount, date: now.toISOString() });

    if (firstThisWeek) events.xp += 20;
    const streak = computeStreak(game.deposits, now);
    if (firstThisWeek && streak > 1) events.xp += Math.min(50, streak * 5);

    // Milestones are measured against the (re-calculated) projected target.
    const after = planAll(state.profile, state.goals, now);
    const plan = after.plans[goalId];
    goal.reachedMilestones = goal.reachedMilestones || [];
    for (const m of MILESTONES) {
      const amt = (plan ? plan.projectedTarget : targetAt(goal, 0, now)) * m.pct / 100;
      if (goal.saved >= amt - 0.5 && goal.reachedMilestones.indexOf(m.pct) === -1) {
        if (m.pct === 100 && goal.saved < targetAt(goal, 0, now) - 0.5) continue;
        goal.reachedMilestones.push(m.pct);
        events.milestones.push({ pct: m.pct, title: m.title, xp: m.xp });
        events.xp += m.xp;
        if (m.badge) events.badges.push(m.badge);
      }
    }
    if (goal.saved >= targetAt(goal, 0, now) - 0.5) {
      goal.status = 'completed';
      goal.completedAt = now.toISOString();
      events.completed = true;
      if (goal.reachedMilestones.indexOf(100) === -1) {
        goal.reachedMilestones.push(100);
        events.milestones.push({ pct: 100, title: MILESTONES[4].title, xp: MILESTONES[4].xp });
        events.xp += MILESTONES[4].xp;
        events.badges.push('goal_done');
      }
    }

    events.badges.push('first_deposit');
    if (streak >= 4) events.badges.push('streak_4');
    if (streak >= 12) events.badges.push('streak_12');
    if (!overSurplus && after.analysis.emergencyGap <= 0) events.badges.push('safe_saver');

    game.xp += events.xp;
    const lv = levelFromXp(game.xp);
    if (lv.level >= 5) events.badges.push('level_5');
    if (lv.level > levelBefore) events.levelUp = lv;

    events.badges = grantBadges(game, events.badges, now);
    events.streak = streak;
    logHistory(game, now, 'deposit', { goalId, amount, xp: events.xp });
    events.milestones.forEach((m) => logHistory(game, now, 'milestone', { goalId, pct: m.pct, xp: m.xp }));
    if (events.completed) logHistory(game, now, 'complete', { goalId });
    return events;
  }

  /** Give badges the user doesn't have yet; return only the new ones. */
  function grantBadges(game, ids, now) {
    game.badges = game.badges || {};
    const fresh = [];
    for (const id of ids) {
      if (!BADGES[id] || game.badges[id]) continue;
      game.badges[id] = toDate(now).toISOString();
      fresh.push(id);
      logHistory(game, now, 'badge', { badge: id });
    }
    return fresh;
  }

  function logHistory(game, now, type, data) {
    game.history = game.history || [];
    game.history.unshift(Object.assign({ type, date: toDate(now).toISOString() }, data));
    if (game.history.length > 200) game.history.length = 200;
  }

  return {
    // constants
    MAX_MONTHS, SAFETY_BUFFER, ASSET_RULES, SCENARIOS, MILESTONES, FEASIBILITY, LEVELS, BADGES, PRIORITY_WEIGHT,
    // helpers
    addMonths, monthsBetween, targetAt, monthlyRate,
    // engine
    analyzeProfile, requiredMonthly, allocate, simulatePortfolio, planAll, whatIf,
    buildMilestones, cadenceOf, scheduleStatus, pressureOf,
    diffPlans, profileChangeReasons,
    // gamification
    levelFromXp, computeStreak, weekIndex, applyDeposit, grantBadges, logHistory,
  };
});
