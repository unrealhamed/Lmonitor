/*
 * Investment engine — portfolio, risk, rebalancing, Iran market analysis, signals.
 * Pure functions (browser: window.FinInvest, Node: require).
 *
 * MARKET below is a SAMPLE snapshot. In production, replace `MarketProvider.fetch()`
 * with real feeds (e.g. a TGJU/Bonbast-style domestic feed + a global metals feed).
 * Every value carries `source` and `asOf`, and nothing here is a forecast.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.FinInvest = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const OZ = 31.1035; // grams per troy ounce

  /* ---------------- Market snapshot (sample data) ---------------- */
  const MARKET = {
    sample: true,
    asOf: '2026-11-08T10:30:00+03:30',
    fx: { usd: { name: 'دلار آمریکا (بازار آزاد)', buy: 121500, sell: 120500, ch24: 0.6, source: 'نمونه — فید ارز داخلی' },
          eur: { name: 'یورو', buy: 139800, sell: 138600, ch24: 0.4, source: 'نمونه — فید ارز داخلی' },
          aed: { name: 'درهم امارات', buy: 33150, sell: 32850, ch24: 0.5, source: 'نمونه — فید ارز داخلی' } },
    global: { goldOz: { name: 'اونس جهانی طلا', usd: 4012, ch24: -0.3, source: 'نمونه — فید جهانی فلزات' },
              silverOz: { name: 'اونس نقره', usd: 49.6, ch24: 1.1, source: 'نمونه — فید جهانی فلزات' },
              copperT: { name: 'مس (تن)', usd: 10480, ch24: 0.2, source: 'نمونه — LME' } },
    domestic: {
      gold18: { name: 'طلای ۱۸ عیار (گرم)', buy: 12290000, sell: 11980000, ch24: 0.4, unit: 'گرم', source: 'نمونه — بازار طلای تهران' },
      coin:   { name: 'سکه امامی', buy: 124500000, sell: 122800000, ch24: 0.9, unit: 'عدد', source: 'نمونه — بازار سکه' },
      silver: { name: 'نقره ۹۹۹ (گرم)', buy: 214000, sell: 203000, ch24: 1.4, unit: 'گرم', source: 'نمونه — بازار نقره' },
      copper: { name: 'مس کاتد (کیلوگرم)', buy: 1365000, sell: 1330000, ch24: 0.1, unit: 'کیلوگرم', source: 'نمونه — بورس کالا' },
    },
    macro: { inflation: 0.38, depositRate: 0.23, inflationSource: 'نمونه — مرکز آمار (نقطه‌به‌نقطه)', rateSource: 'نمونه — سقف سود سپرده یک‌ساله' },
    // 12-month historical changes (history, not forecast)
    history12m: { inflation: 0.38, usd: 0.31, gold18: 0.44, tedpix: 0.27, deposit: 0.23 },
  };

  // Instruments the user can hold. price() returns what you'd GET when selling (bid) and pay when buying (ask).
  const ASSETS = {
    usd:    { name: 'دلار', cls: 'fx',       unit: 'دلار',   q: (m) => m.fx.usd,          fee: 0.003, liquidity: 'بالا', taxNote: 'بدون مالیات بر عایدی' },
    gold18: { name: 'طلای ۱۸ عیار', cls: 'gold', unit: 'گرم', q: (m) => m.domestic.gold18, fee: 0.07, liquidity: 'بالا', taxNote: 'اجرت و سود فروشنده در خرید فیزیکی' },
    coin:   { name: 'سکه امامی', cls: 'gold',   unit: 'عدد',   q: (m) => m.domestic.coin,   fee: 0.01, liquidity: 'بالا', taxNote: 'مشمول مالیات بر عایدی در خریدهای بالای سقف' },
    goldfund:{ name: 'صندوق طلا', cls: 'gold',   unit: 'واحد', q: () => ({ buy: 41800, sell: 41650, ch24: 0.5, source: 'نمونه — NAV صندوق' }), fee: 0.0024, liquidity: 'خیلی بالا', taxNote: 'بدون مالیات' },
    equityfund:{ name: 'صندوق سهامی', cls: 'equity', unit: 'واحد', q: () => ({ buy: 25400, sell: 25150, ch24: -0.8, source: 'نمونه — NAV صندوق' }), fee: 0.006, liquidity: 'بالا', taxNote: 'بدون مالیات' },
    stock:  { name: 'سهام بورس (سبد)', cls: 'equity', unit: 'تومان', q: () => ({ buy: 1, sell: 0.97, ch24: -1.2, source: 'نمونه — TSETMC' }), fee: 0.012, liquidity: 'متوسط', taxNote: 'مالیات نقل‌وانتقال ۰٫۵٪' },
    fixedfund:{ name: 'صندوق درآمد ثابت', cls: 'fixed', unit: 'واحد', q: () => ({ buy: 18950, sell: 18950, ch24: 0.06, source: 'نمونه — NAV صندوق' }), fee: 0.001, liquidity: 'خیلی بالا', taxNote: 'بدون مالیات' },
    silver: { name: 'نقره', cls: 'commodity', unit: 'گرم', q: (m) => m.domestic.silver, fee: 0.05, liquidity: 'متوسط', taxNote: '' },
    crypto: { name: 'رمزارز (تتر/بیت‌کوین)', cls: 'crypto', unit: 'تومان', q: () => ({ buy: 1, sell: 1, ch24: 2.4, source: 'نمونه — صرافی داخلی' }), fee: 0.004, liquidity: 'بالا', taxNote: 'ریسک مقرراتی' },
  };

  const CLASSES = {
    fixed:     { name: 'درآمد ثابت/سپرده', color: '#1d77ac', risk: 1 },
    gold:      { name: 'طلا و سکه',        color: '#f2b33d', risk: 2 },
    fx:        { name: 'ارز',              color: '#2fd9a6', risk: 2 },
    equity:    { name: 'سهام و صندوق سهامی', color: '#124266', risk: 4 },
    commodity: { name: 'نقره و فلزات',     color: '#9fb6c6', risk: 3 },
    crypto:    { name: 'رمزارز',           color: '#ff7a66', risk: 5 },
  };

  // Target allocation per risk profile (sums to 1). Educational model, not advice.
  const PROFILES = {
    conservative: { name: 'محافظه‌کار', target: { fixed: 0.55, gold: 0.25, fx: 0.10, equity: 0.10, commodity: 0, crypto: 0 } },
    balanced:     { name: 'متعادل',     target: { fixed: 0.35, gold: 0.25, fx: 0.10, equity: 0.25, commodity: 0.05, crypto: 0 } },
    growth:       { name: 'رشد',        target: { fixed: 0.20, gold: 0.20, fx: 0.10, equity: 0.40, commodity: 0.05, crypto: 0.05 } },
    aggressive:   { name: 'تهاجمی',     target: { fixed: 0.10, gold: 0.15, fx: 0.05, equity: 0.55, commodity: 0.05, crypto: 0.10 } },
  };
  const PROFILE_ORDER = ['conservative', 'balanced', 'growth', 'aggressive'];

  const QUESTIONS = [
    { q: 'اگر ارزش سرمایه‌ات در یک ماه ۲۰٪ افت کند چه می‌کنی؟', a: ['همه را می‌فروشم', 'بخشی را می‌فروشم', 'صبر می‌کنم', 'بیشتر می‌خرم'] },
    { q: 'این پول را حداقل چه مدت لازم نداری؟', a: ['کمتر از ۶ ماه', '۶ ماه تا ۲ سال', '۲ تا ۵ سال', 'بیشتر از ۵ سال'] },
    { q: 'هدف اصلی‌ات از سرمایه‌گذاری؟', a: ['حفظ ارزش پول', 'کمی بیشتر از تورم', 'رشد قابل‌توجه', 'حداکثر رشد با ریسک بالا'] },
    { q: 'تجربه‌ات در بازار سرمایه؟', a: ['هیچ', 'کم (سپرده/طلا)', 'متوسط (صندوق/سهام)', 'زیاد'] },
    { q: 'درآمدت چقدر پایدار است؟', a: ['ناپایدار', 'تا حدی', 'پایدار', 'خیلی پایدار با پشتوانه'] },
  ];

  /* ---------------- Iran-specific valuation ---------------- */
  function intrinsic(m) {
    const usd = m.fx.usd.sell;
    const gold18 = m.global.goldOz.usd * usd * 0.75 / OZ;          // 18k = 750/1000
    const coin = m.global.goldOz.usd * usd * 8.133 * 0.9 / OZ;     // Emami: 8.133g at 900/1000
    const silver = m.global.silverOz.usd * usd * 0.999 / OZ;
    const copper = m.global.copperT.usd * usd / 1000;              // per kg
    const bubble = (mkt, iv) => (mkt - iv) / iv;
    const mid = (x) => (x.buy + x.sell) / 2;
    return {
      gold18: { iv: gold18, market: mid(m.domestic.gold18), bubble: bubble(mid(m.domestic.gold18), gold18) },
      coin:   { iv: coin,   market: mid(m.domestic.coin),   bubble: bubble(mid(m.domestic.coin), coin) },
      silver: { iv: silver, market: mid(m.domestic.silver), bubble: bubble(mid(m.domestic.silver), silver) },
      copper: { iv: copper, market: mid(m.domestic.copper), bubble: bubble(mid(m.domestic.copper), copper) },
    };
  }
  const spread = (x) => (x.buy - x.sell) / x.buy;
  const realRate = (m) => (1 + m.macro.depositRate) / (1 + m.macro.inflation) - 1;

  /* ---------------- Portfolio from transactions ---------------- */
  // tx: { id, asset, side:'buy'|'sell', qty, price, fee, date, external }
  function holdings(txs, m) {
    const h = {};
    let realized = 0, fees = 0;
    txs.slice().sort((a, b) => new Date(a.date) - new Date(b.date)).forEach((t) => {
      const x = h[t.asset] || (h[t.asset] = { asset: t.asset, qty: 0, cost: 0, realized: 0, external: false });
      fees += t.fee || 0;
      if (t.external) x.external = true;
      if (t.side === 'buy') { x.cost += t.qty * t.price + (t.fee || 0); x.qty += t.qty; }
      else {
        const q = Math.min(t.qty, x.qty);
        const avg = x.qty ? x.cost / x.qty : 0;
        const pnl = q * t.price - (t.fee || 0) - q * avg;
        x.realized += pnl; realized += pnl;
        x.cost -= q * avg; x.qty -= q;
      }
    });
    const list = Object.values(h).filter((x) => x.qty > 1e-9).map((x) => {
      const A = ASSETS[x.asset], quote = A.q(m);
      const gross = x.qty * quote.sell;
      const exitCost = gross * A.fee;
      const value = gross - exitCost;                 // what you'd actually receive
      return Object.assign(x, {
        name: A.name, cls: A.cls, unit: A.unit, price: quote.sell, ask: quote.buy, ch24: quote.ch24, source: quote.source,
        avg: x.cost / x.qty, gross, exitCost, value,
        unrealized: value - x.cost, changePct: x.cost ? (value - x.cost) / x.cost : 0,
      });
    });
    const total = list.reduce((s, x) => s + x.value, 0);
    list.forEach((x) => { x.weight = total ? x.value / total : 0; });
    const cost = list.reduce((s, x) => s + x.cost, 0);
    const byClass = {};
    Object.keys(CLASSES).forEach((k) => { byClass[k] = 0; });
    list.forEach((x) => { byClass[x.cls] += x.value; });
    Object.keys(byClass).forEach((k) => { byClass[k] = total ? byClass[k] / total : 0; });
    return { list: list.sort((a, b) => b.value - a.value), total, cost, unrealized: total - cost, realized, fees, byClass,
             returnPct: cost ? (total - cost) / cost : 0 };
  }

  /* ---------------- Risk: tolerance AND capacity ---------------- */
  function riskProfile(answers, finance) {
    const answered = (answers || []).filter((a) => a != null).length;
    if (answered < QUESTIONS.length) return { complete: false, answered };
    const tolerance = answers.reduce((s, a) => s + a, 0) / (QUESTIONS.length * 3) * 100; // 0..100
    // capacity: what the finances can actually absorb (not psychology)
    let capacity = 50;
    capacity += (finance.emergencyRatio - 0.5) * 40;            // emergency fund
    capacity += Math.min(0.4, finance.savingsRate) * 50 - 10;    // savings rate
    capacity -= Math.min(30, finance.debtRatio * 100);           // debt burden
    if (finance.nearestGoalMonths != null && finance.nearestGoalMonths < 12) capacity -= 15; // short horizon money
    capacity = Math.max(0, Math.min(100, capacity));
    const score = Math.min(tolerance, capacity + 10);            // the lower one wins
    const idx = score < 30 ? 0 : score < 55 ? 1 : score < 75 ? 2 : 3;
    const key = PROFILE_ORDER[idx];
    return { complete: true, tolerance, capacity, score, key, name: PROFILES[key].name, target: PROFILES[key].target,
             limitedBy: capacity + 10 < tolerance ? 'capacity' : 'tolerance' };
  }

  /* ---------------- Rebalancing ---------------- */
  function rebalance(pf, risk, threshold) {
    if (!risk.complete || pf.total <= 0) return { ready: false, moves: [] };
    threshold = threshold == null ? 0.05 : threshold;
    const moves = Object.keys(CLASSES).map((k) => {
      const diff = pf.byClass[k] - risk.target[k];
      return { cls: k, name: CLASSES[k].name, current: pf.byClass[k], target: risk.target[k], diff, amount: Math.abs(diff) * pf.total, action: diff > 0 ? 'sell' : 'buy' };
    }).filter((x) => Math.abs(x.diff) >= threshold);
    const tradeVolume = moves.reduce((s, x) => s + x.amount, 0) / 2;
    const estCost = tradeVolume * 0.012; // blended fee + spread estimate
    return { ready: true, moves, drift: Math.max(0, ...Object.keys(CLASSES).map((k) => Math.abs(pf.byClass[k] - risk.target[k]))), estCost };
  }

  /* ---------------- Suggestions (explainable, never "buy X") ---------------- */
  function suggestions(pf, risk, finance) {
    const out = [];
    const top = Object.keys(pf.byClass).sort((a, b) => pf.byClass[b] - pf.byClass[a])[0];
    if (pf.byClass[top] > 0.5) out.push({ tone: 'coral', icon: '🎯', title: 'تمرکز بالا', text: pct(pf.byClass[top]) + ' سبدت در «' + CLASSES[top].name + '» است. تنوع کمتر یعنی حساسیت بیشتر به یک بازار.' });
    if (finance.emergencyRatio < 1) out.push({ tone: 'coral', icon: '🛡️', title: 'نقدینگی اضطراری ناکافی', text: 'صندوق اضطراری ' + pct(finance.emergencyRatio) + ' کامل است. قبل از سرمایه‌گذاری پرریسک، آن را کامل کن.' });
    const risky = pf.byClass.equity + pf.byClass.crypto + pf.byClass.commodity;
    if (finance.nearestGoalMonths != null && finance.nearestGoalMonths < 12 && risky > 0.3) out.push({ tone: 'amber', icon: '⏳', title: 'عدم تناسب با افق هدف', text: 'نزدیک‌ترین هدفت ' + finance.nearestGoalMonths + ' ماه دیگر است ولی ' + pct(risky) + ' سبد در دارایی‌های پرنوسان است.' });
    if (risk.complete) {
      const riskyTarget = risk.target.equity + risk.target.crypto + risk.target.commodity;
      if (risky > riskyTarget + 0.1) out.push({ tone: 'red', icon: '⚠️', title: 'ریسک بیشتر از ظرفیت', text: 'وزن دارایی‌های پرریسک ' + pct(risky) + ' است؛ برای پروفایل «' + risk.name + '» حدود ' + pct(riskyTarget) + ' مناسب‌تر است.' });
    } else out.push({ tone: 'navy', icon: '📝', title: 'اطلاعات کافی نیست', text: 'تا پرسشنامه ریسک کامل نشود، پیشنهاد ترکیب سبد صادر نمی‌شود.' });
    if (pf.byClass.fixed < 0.05 && pf.total > 0) out.push({ tone: 'amber', icon: '💧', title: 'نقدشوندگی سبد', text: 'تقریباً هیچ دارایی کم‌ریسک و نقدشونده‌ای نداری.' });
    if (!out.length) out.push({ tone: 'mint', icon: '✅', title: 'سبد متعادل', text: 'نکته‌ی هشداردهنده‌ای پیدا نشد. هر سه ماه بازبینی کن.' });
    return out;
  }
  const pct = (x) => Math.round(x * 100) + '٪';

  /* ---------------- Opportunity signals ---------------- */
  // Each signal: reason, source, asOf, confidence. Wording is conditional, never an instruction.
  function signals(m) {
    const iv = intrinsic(m);
    const age = (Date.now() - new Date(m.asOf)) / 36e5; // hours
    const conf = (base) => Math.max(0.2, base - (m.sample ? 0.25 : 0) - (age > 24 ? 0.2 : 0));
    const out = [];
    const b = iv.coin.bubble;
    out.push(b > 0.08
      ? { type: 'caution', asset: 'سکه امامی', title: 'حباب سکه بالاست', reason: 'قیمت بازار ' + pct(b) + ' بالاتر از ارزش ذاتی (اونس × دلار × وزن) است. حباب معمولاً در آرامش بازار تخلیه می‌شود.', alt: 'برای خرید طلا، طلای آب‌شده یا صندوق طلا حباب کمتری دارند.', confidence: conf(0.75) }
      : { type: 'opportunity', asset: 'سکه امامی', title: 'حباب سکه پایین است', reason: 'اختلاف بازار با ارزش ذاتی ' + pct(b) + ' است.', alt: '', confidence: conf(0.6) });
    const g = iv.gold18.bubble;
    out.push({ type: Math.abs(g) < 0.04 ? 'neutral' : g > 0 ? 'caution' : 'opportunity', asset: 'طلای ۱۸', title: 'فاصله طلا با ارزش جهانی: ' + pct(g), reason: 'ارزش ذاتی هر گرم ' + Math.round(iv.gold18.iv).toLocaleString('en-US') + ' تومان با دلار ' + m.fx.usd.sell.toLocaleString('en-US') + ' و اونس $' + m.global.goldOz.usd + '.', alt: 'در خرید فیزیکی اجرت و سود (~۷٪) را هم حساب کن.', confidence: conf(0.7) });
    const rr = realRate(m);
    out.push({ type: rr < 0 ? 'caution' : 'opportunity', asset: 'سپرده و درآمد ثابت', title: 'نرخ بهره واقعی ' + pct(rr), reason: 'سود سپرده ' + pct(m.macro.depositRate) + ' در برابر تورم ' + pct(m.macro.inflation) + '. ' + (rr < 0 ? 'نگهداری طولانی پول در سپرده قدرت خرید را کم می‌کند.' : 'سپرده بازده واقعی مثبت دارد.'), alt: 'برای پول اهداف کوتاه‌مدت، نقدشوندگی مهم‌تر از بازده است.', confidence: conf(0.8) });
    const s = iv.silver.bubble;
    if (s > 0.1) out.push({ type: 'caution', asset: 'نقره', title: 'نقره داخلی گران‌تر از جهانی', reason: 'حباب ' + pct(s) + ' و اختلاف خرید/فروش ' + pct(spread(m.domestic.silver)) + '. هزینه ورود و خروج بالاست.', alt: '', confidence: conf(0.6) });
    const sp = spread(m.domestic.gold18);
    if (sp > 0.02) out.push({ type: 'neutral', asset: 'طلای ۱۸', title: 'اختلاف خرید و فروش ' + pct(sp), reason: 'برای سود، قیمت باید دست‌کم همین مقدار + اجرت بالا برود.', alt: '', confidence: conf(0.9) });
    return out.map((x) => Object.assign(x, { source: 'محاسبه از داده‌های بازار — ' + (m.sample ? 'داده نمونه' : 'داده زنده'), asOf: m.asOf }));
  }

  /* ---------------- Benchmark comparison (historical) ---------------- */
  function compare(pf, m) {
    return [
      { key: 'portfolio', name: 'سبد من', ret: pf.returnPct, mine: true },
      { key: 'inflation', name: 'تورم', ret: m.history12m.inflation },
      { key: 'gold18', name: 'طلای ۱۸', ret: m.history12m.gold18 },
      { key: 'usd', name: 'دلار', ret: m.history12m.usd },
      { key: 'tedpix', name: 'شاخص کل بورس', ret: m.history12m.tedpix },
      { key: 'deposit', name: 'سپرده بانکی', ret: m.history12m.deposit },
    ];
  }

  /* Swap this for real feeds; the UI only depends on the MARKET shape. */
  const MarketProvider = { fetch: () => Promise.resolve(MARKET) };

  function seedTransactions(now) {
    const d = (days) => new Date(now.getTime() - days * 864e5).toISOString();
    return [
      { id: 't1', asset: 'equityfund', side: 'buy', qty: 260, price: 23100, fee: 36000, date: d(240) },
      { id: 't2', asset: 'goldfund', side: 'buy', qty: 60, price: 30500, fee: 4400, date: d(200) },
      { id: 't3', asset: 'gold18', side: 'buy', qty: 0.3, price: 9800000, fee: 205000, date: d(180) },
      { id: 't4', asset: 'stock', side: 'buy', qty: 4300000, price: 1, fee: 51600, date: d(150), external: true },
      { id: 't5', asset: 'equityfund', side: 'sell', qty: 40, price: 26100, fee: 6300, date: d(60) },
      { id: 't6', asset: 'usd', side: 'buy', qty: 20, price: 98000, fee: 5900, date: d(120) },
      { id: 't8', asset: 'fixedfund', side: 'buy', qty: 160, price: 16900, fee: 2700, date: d(90) },
      { id: 't7', asset: 'crypto', side: 'buy', qty: 1200000, price: 1, fee: 4800, date: d(40) },
    ];
  }

  return { OZ, MARKET, ASSETS, CLASSES, PROFILES, QUESTIONS, intrinsic, spread, realRate, holdings, riskProfile, rebalance, suggestions, signals, compare, MarketProvider, seedTransactions };
});
