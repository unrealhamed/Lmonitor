/*
 * Demo data for the prototype. The home screen numbers match the design
 * (income 4.2M, expenses 1.85M, net worth 24.85M Toman).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.FinSeed = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function iso(d) { return d.toISOString(); }
  function monthsFrom(now, n, day) {
    const d = new Date(now.getFullYear(), now.getMonth() + n, day || now.getDate(), 12);
    return d;
  }

  function createSeed(now) {
    now = now || new Date();
    const threeMonthsAgo = monthsFrom(now, -3);

    const profile = {
      name: 'امیرمهدی',
      monthlyIncome: 4200000,
      prevIncome: 3750000,
      fixedExpenses: 1100000,
      variableExpenses: 750000,
      prevExpenses: 1990000,
      cash: 8697500,             // includes money already set aside for goals
      emergencyMonths: 3,
      savingsReturn: 0.18,       // annual return of the savings account that holds goal money
      investments: [
        { id: 'i1', name: 'صندوق سهامی', type: 'fund', value: 7000000 },
        { id: 'i2', name: 'سهام بورس', type: 'stock', value: 4182500 },
        { id: 'i3', name: 'طلا و ارز', type: 'gold', value: 3727500 },
        { id: 'i4', name: 'سایر', type: 'other', value: 1242500 },
      ],
      debts: [],
      // net worth for the last 5 months (the 6th = current, computed live)
      netWorthHistory: [18200000, 19900000, 19300000, 21600000, 20900000],
      prevNetWorth: 22925000,
    };

    const goals = [
      {
        id: 'g1', name: 'PlayStation 5', emoji: '🎮', image: null, category: 'gadget',
        price: 22000000, priceDate: iso(now), inflation: 0.15,
        saved: 2000000, deadline: iso(monthsFrom(now, 20)), priority: 'high', rank: 0,
        scenario: 'normal', status: 'active', createdAt: iso(threeMonthsAgo),
        reachedMilestones: [],
        baseline: { date: iso(threeMonthsAgo), saved: 200000, monthly: 800000 },
        changes: [],
      },
      {
        id: 'g2', name: 'سفر شمال', emoji: '🏖️', image: null, category: 'travel',
        price: 5000000, priceDate: iso(now), inflation: 0.10,
        saved: 1000000, deadline: iso(monthsFrom(now, 12)), priority: 'medium', rank: 1,
        scenario: 'normal', status: 'active', createdAt: iso(monthsFrom(now, -1)),
        reachedMilestones: [10],
        baseline: { date: iso(monthsFrom(now, -1)), saved: 700000, monthly: 300000 },
        changes: [],
      },
      {
        id: 'g3', name: 'لپ‌تاپ گیمینگ', emoji: '💻', image: null, category: 'gadget',
        price: 30000000, priceDate: iso(now), inflation: 0.15,
        saved: 0, deadline: iso(monthsFrom(now, 30)), priority: 'low', rank: 2,
        scenario: 'normal', status: 'active', createdAt: iso(now),
        reachedMilestones: [],
        baseline: null,
        changes: [],
      },
      {
        id: 'g0', name: 'هدفون بی‌سیم', emoji: '🎧', image: null, category: 'gadget',
        price: 3500000, priceDate: iso(monthsFrom(now, -5)), inflation: 0.15,
        saved: 3500000, deadline: iso(monthsFrom(now, -1)), priority: 'medium', rank: 9,
        scenario: 'normal', status: 'completed', createdAt: iso(monthsFrom(now, -6)),
        completedAt: iso(monthsFrom(now, -1)),
        reachedMilestones: [10, 25, 50, 75, 100], baseline: null, changes: [],
      },
    ];

    // two consecutive weekly deposits so the streak is alive
    const game = {
      xp: 340,
      badges: {
        first_goal: iso(monthsFrom(now, -6)),
        first_deposit: iso(monthsFrom(now, -6)),
        quarter: iso(monthsFrom(now, -4)),
        halfway: iso(monthsFrom(now, -3)),
        goal_done: iso(monthsFrom(now, -1)),
        multi_goal: iso(monthsFrom(now, -1)),
      },
      deposits: [
        { id: 'd1', goalId: 'g1', amount: 600000, date: iso(new Date(now.getTime() - 14 * 864e5)) },
        { id: 'd2', goalId: 'g2', amount: 300000, date: iso(new Date(now.getTime() - 7 * 864e5)) },
      ],
      history: [
        { type: 'deposit', goalId: 'g2', amount: 300000, xp: 25, date: iso(new Date(now.getTime() - 7 * 864e5)) },
        { type: 'deposit', goalId: 'g1', amount: 600000, xp: 20, date: iso(new Date(now.getTime() - 14 * 864e5)) },
        { type: 'complete', goalId: 'g0', date: iso(monthsFrom(now, -1)) },
        { type: 'badge', badge: 'goal_done', date: iso(monthsFrom(now, -1)) },
        { type: 'badge', badge: 'halfway', date: iso(monthsFrom(now, -3)) },
      ],
    };

    return { version: 1, profile, goals, game };
  }

  return { createSeed };
});
