/*
 * Smart Financial Goals — UI layer (vanilla JS, no build step).
 * Views: home · goals · goal · achievements · assets
 * Overlays: goal form · deposit · more menu · celebration
 */
(function () {
  'use strict';

  const E = window.FinEngine;
  const STORE_KEY = 'lmonitor-finance-v1';

  /* ================================================================== */
  /* State                                                              */
  /* ================================================================== */

  let state = load() || window.FinSeed.createSeed(new Date());
  const ui = {
    view: 'home', goalId: null, hidden: false, cadence: 'weekly',
    whatIf: { extra: 0, income: 0, lump: false, invest: false },
  };

  function load() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (!raw) return null;
      const s = JSON.parse(raw);
      return s && s.version === 1 ? s : null;
    } catch (e) { return null; }
  }
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { /* private mode: keep in memory */ }
  }
  const now = () => new Date();
  const plan = () => E.planAll(state.profile, state.goals, now());

  /* ================================================================== */
  /* Formatting                                                         */
  /* ================================================================== */

  const faDigits = (s) => String(s).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);
  const fa = (n) => faDigits(Math.round(n || 0).toLocaleString('en-US'));
  const faN = (n, d) => faDigits(Number(n || 0).toFixed(d || 0).replace(/\.0+$/, ''));
  const pct = (x, d) => '<bdi>' + faN(x * 100, d == null ? 0 : d) + '٪</bdi>';
  const pctT = (x, d) => faN(x * 100, d == null ? 0 : d) + '٪'; // plain text (attributes, dialogs)
  const compact = (n) => {
    const a = Math.abs(n);
    if (a >= 1e9) return faN(n / 1e9, 1) + 'B';
    if (a >= 1e6) return faN(n / 1e6, 1) + 'M';
    if (a >= 1e3) return faN(n / 1e3, 0) + 'K';
    return fa(n);
  };
  const toman = (n) => fa(n) + ' تومان';
  const signed = (n) => (n > 0 ? '+' : n < 0 ? '−' : '') + fa(Math.abs(n));
  let jFmt, jMonthFmt, jDayFmt;
  try {
    jFmt = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: 'long' });
    jMonthFmt = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { month: 'long' });
    jDayFmt = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { day: 'numeric', month: 'long' });
  } catch (e) {
    jFmt = jMonthFmt = jDayFmt = new Intl.DateTimeFormat('fa-IR', { year: 'numeric', month: 'long' });
  }
  const jDate = (d) => (d ? jFmt.format(new Date(d)) : '—');
  const jMonth = (d) => jMonthFmt.format(new Date(d));
  const jDay = (d) => jDayFmt.format(new Date(d));
  function duration(m) { return '<bdi>' + durationT(m) + '</bdi>'; }
  function durationT(m) {
    if (!isFinite(m)) return 'نامشخص';
    if (m <= 0) return 'همین حالا';
    const y = Math.floor(m / 12), r = m % 12;
    if (!y) return faN(r) + ' ماه';
    return faN(y) + ' سال' + (r ? ' و ' + faN(r) + ' ماه' : '');
  }
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function parseMoney(v) {
    const latin = String(v || '').replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[٠-٩]/g, (d) => '٠١٢٣٤٥٦٧٨٩'.indexOf(d));
    const n = parseInt(latin.replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : n;
  }
  const uid = () => 'g' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);

  /* ================================================================== */
  /* Icons                                                              */
  /* ================================================================== */

  const I = {
    search: '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    bell: '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/></svg>',
    bolt: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"/></svg>',
    eye: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>',
    bars: '<svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><rect x="3.5" y="12" width="4" height="8.5" rx="1.6"/><rect x="10" y="7.5" width="4" height="13" rx="1.6"/><rect x="16.5" y="3.5" width="4" height="17" rx="1.6"/></svg>',
    wallet: '<svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h10a1 1 0 0 1 0 2h-10a.5.5 0 0 0 0 1H18a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6.5A2.5 2.5 0 0 1 4 17.5v-11Zm12 7.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"/></svg>',
    target: '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><path d="m13 11 7-7M17 4h3v3"/></svg>',
    pie: '<svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><path d="M11 3.1A9 9 0 1 0 20.9 13H11V3.1Z"/><path d="M13 2.1V11h8.9A9 9 0 0 0 13 2.1Z"/></svg>',
    up: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
    down: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>',
    triUp: '<svg width="11" height="11" viewBox="0 0 10 10" fill="currentColor"><path d="M5 1.5 9.3 8.5H.7z"/></svg>',
    triDown: '<svg width="11" height="11" viewBox="0 0 10 10" fill="currentColor"><path d="M5 8.5.7 1.5h8.6z"/></svg>',
    caret: '<svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M5 8 1 3h8z"/></svg>',
    arrowL: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>',
    back: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>',
    brief: '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M9 3h6a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v3H2V8a2 2 0 0 1 2-2h3V5a2 2 0 0 1 2-2Zm0 3h6V5H9v1Z"/><path d="M2 13h8v1a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-1h8v5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5Z"/></svg>',
    plus: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
    edit: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
    trash: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>',
    chevUp: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="m6 15 6-6 6 6"/></svg>',
    chevDown: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="m6 9 6 6 6-6"/></svg>',
  };

  const AVATAR = '<svg viewBox="0 0 60 60" aria-hidden="true"><defs><linearGradient id="avbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfe3ec"/><stop offset="1" stop-color="#8fb7c9"/></linearGradient></defs><rect width="60" height="60" fill="url(#avbg)"/><path d="M8 60c2-12 11-17 22-17s20 5 22 17Z" fill="#1f8f86"/><path d="M24 40h12v6a6 6 0 0 1-12 0Z" fill="#c98d63"/><ellipse cx="30" cy="28" rx="11" ry="13" fill="#d9a179"/><path d="M18 26c-1-10 6-15 13-15 8 0 13 6 11 15-2-4-5-6-8-6-5 0-8 2-16 6Z" fill="#2b1d17"/><rect x="20" y="26" width="9" height="5" rx="2.2" fill="#0c2238"/><rect x="31" y="26" width="9" height="5" rx="2.2" fill="#0c2238"/><path d="M29 28h2" stroke="#0c2238" stroke-width="1.5"/><path d="M26 36q4 2.5 8 0" stroke="#8a4b33" stroke-width="1.4" fill="none" stroke-linecap="round"/></svg>';

  const GOAL_COLORS = ['#2fd9a6', '#1d77ac', '#f59342', '#124266', '#f2b33d', '#ff7a66', '#8b7cf6'];
  const EMOJIS = ['🎮', '💻', '📱', '🚗', '🏠', '✈️', '🏖️', '🎓', '💍', '🚀', '🎸', '💰'];
  const PRIORITY = { high: 'زیاد', medium: 'متوسط', low: 'کم' };

  /* ================================================================== */
  /* Small render helpers                                               */
  /* ================================================================== */

  function smoothPath(pts) {
    if (pts.length < 2) return '';
    let d = 'M' + pts[0][0].toFixed(1) + ',' + pts[0][1].toFixed(1);
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += ' C' + c1.map((v) => v.toFixed(1)) + ' ' + c2.map((v) => v.toFixed(1)) + ' ' + p2.map((v) => v.toFixed(1));
    }
    return d;
  }

  let ringSeq = 0;
  function ring(size, stroke, progress, center, opts) {
    opts = opts || {};
    const r = (size - stroke) / 2, c = 2 * Math.PI * r;
    const off = c * (1 - Math.max(0, Math.min(1, progress)));
    const id = 'rg' + (++ringSeq);
    const track = opts.dark ? 'rgba(255,255,255,.12)' : 'rgba(13,51,82,.08)';
    return '<div class="ring" style="width:' + size + 'px;height:' + size + 'px">' +
      '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '">' +
      '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + (opts.c1 || '#2fd9a6') + '"/><stop offset="1" stop-color="' + (opts.c2 || '#1d77ac') + '"/></linearGradient></defs>' +
      '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="' + track + '" stroke-width="' + stroke + '"/>' +
      '<circle class="ring-anim" cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="url(#' + id + ')" stroke-width="' + stroke + '" stroke-linecap="round" stroke-dasharray="' + c.toFixed(2) + '" stroke-dashoffset="' + c.toFixed(2) + '" data-off="' + off.toFixed(2) + '"/>' +
      '</svg><div class="center">' + center + '</div></div>';
  }
  const goalVisual = (g) => g.image ? '<img src="' + esc(g.image) + '" alt="">' : '<span class="emoji">' + esc(g.emoji || '🎯') + '</span>';
  const feasPill = (p) => '<span class="pill rtl ' + p.feasibilityInfo.tone + '">' + p.feasibilityInfo.label + '</span>';

  function topbar(title, back, extra) {
    return '<div class="topbar"><button class="icon-btn" data-go="' + back + '" aria-label="بازگشت">' + I.back + '</button>' +
      '<h1>' + title + '</h1>' + (extra || '') + '</div>';
  }

  /* ================================================================== */
  /* View: Home (the reference design)                                  */
  /* ================================================================== */

  function viewHome() {
    const P = plan();
    const a = P.analysis, p = state.profile, t = now();
    const nwChange = p.prevNetWorth ? (a.netWorth - p.prevNetWorth) / p.prevNetWorth : 0;
    const incChange = p.prevIncome ? (a.income - p.prevIncome) / p.prevIncome : 0;
    const expChange = p.prevExpenses ? (a.expenses - p.prevExpenses) / p.prevExpenses : 0;

    // decorative spark line in the hero: real history, with gentle wiggle between points
    const hist = (p.netWorthHistory || []).concat([a.netWorth]);
    const sparkPts = [];
    const W = 220, H = 150, lo = Math.min.apply(null, hist) * 0.92, hi = Math.max.apply(null, hist);
    hist.forEach((v, i) => {
      const x = 10 + i * (W - 20) / (hist.length - 1);
      const y = H - 10 - (v - lo) / (hi - lo || 1) * (H - 30);
      sparkPts.push([x, y]);
      if (i < hist.length - 1) {
        const nv = hist[i + 1];
        const nx = 10 + (i + 1) * (W - 20) / (hist.length - 1);
        const ny = H - 10 - (nv - lo) / (hi - lo || 1) * (H - 30);
        sparkPts.push([(x + nx) / 2, (y + ny) / 2 + (i % 2 ? -10 : 8)]);
      }
    });
    const last = sparkPts[sparkPts.length - 1];

    // 6-month trend
    const months = hist.map((_, i) => E.addMonths(t, i - hist.length + 1));
    const tw = 220, th = 190, x0 = 14, x1 = 206, y0 = 34, y1 = 150;
    const tLo = Math.min.apply(null, hist) * 0.85, tHi = Math.max.apply(null, hist) * 1.02;
    const tp = hist.map((v, i) => [x0 + i * (x1 - x0) / (hist.length - 1), y1 - (v - tLo) / (tHi - tLo) * (y1 - y0)]);
    const tPath = smoothPath(tp);
    const tl = tp[tp.length - 1];

    // asset distribution
    const inv = a.investments;
    const sumType = (types) => inv.filter((i) => types.indexOf(i.type) !== -1).reduce((s, i) => s + i.value, 0);
    const parts = [
      { label: 'سرمایه‌گذاری‌ها', v: sumType(['fund', 'stock', 'crypto', 'realestate', 'deposit']), c: '#0d3352' },
      { label: 'وجه نقد', v: p.cash, c: '#2fd9a6' },
      { label: 'طلا و ارز', v: sumType(['gold']), c: '#f59342' },
      { label: 'سایر', v: sumType(['other']), c: '#cfdde6' },
    ];
    const tot = parts.reduce((s, x) => s + x.v, 0) || 1;
    const R = 46, C = 2 * Math.PI * R;
    let acc = 0;
    const segs = parts.map((x) => {
      const len = x.v / tot * C;
      const s = '<circle cx="60" cy="60" r="' + R + '" fill="none" stroke="' + x.c + '" stroke-width="20" stroke-dasharray="' + Math.max(0, len - 1.5).toFixed(2) + ' ' + C.toFixed(2) + '" stroke-dashoffset="' + (-acc).toFixed(2) + '"/>';
      acc += len;
      return s;
    }).join('');

    const top = P.ranked[0] ? P.plans[P.ranked[0].id] : null;

    return '<section class="view">' +
      '<header class="header home-header">' +
        '<div class="avatar-wrap"><div class="avatar">' + AVATAR + '</div><span class="online"></span></div>' +
        '<div class="hello"><h1>سلام ' + esc(p.name) + '!</h1><p>' + I.bolt + 'روز خوبی داشته باشی</p></div>' +
        '<button class="icon-btn" data-toast="جستجو به‌زودی اضافه می‌شود" aria-label="جستجو">' + I.search + '</button>' +
        '<button class="icon-btn" data-go="goals" aria-label="اعلان‌ها">' + I.bell + '<span class="dot"></span></button>' +
      '</header>' +

      '<article class="glass-dark networth ' + (ui.hidden ? 'blurred' : '') + '">' +
        '<div class="nw-text">' +
        '<div class="label"><button data-action="toggle-hide" aria-label="نمایش/پنهان">' + I.eye + '</button>ارزش خالص دارایی‌ها</div>' +
        '<div class="amount"><b class="num">' + fa(a.netWorth) + '</b><span>تومان</span></div>' +
        '<div class="compare">نسبت به ماه گذشته <span class="pill solid-mint">' + (nwChange >= 0 ? I.triUp : I.triDown) + ' ' + (nwChange >= 0 ? '+' : '') + pctT(nwChange, 1) + '</span></div>' +
        '</div>' +
        '<svg class="spark" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true">' +
          '<defs><linearGradient id="sparkG" x1="0" x2="1"><stop offset="0" stop-color="#2fd9a6" stop-opacity=".5"/><stop offset="1" stop-color="#5ff0c4"/></linearGradient>' +
          '<filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>' +
          '<path d="' + smoothPath(sparkPts) + '" fill="none" stroke="url(#sparkG)" stroke-width="3" stroke-linecap="round" filter="url(#glow)"/>' +
          '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="5" fill="#bfffe9" stroke="#2fd9a6" stroke-width="3" filter="url(#glow)"/>' +
        '</svg>' +
      '</article>' +

      '<div class="actions">' +
        '<button class="glass action press" data-go="assets">' + I.pie + 'مدیریت سبد</button>' +
        '<button class="glass action press active" data-go="goals">' + I.target + 'هدف‌گذاری</button>' +
        '<button class="glass action press" data-action="deposit" data-id="' + (top ? top.goalId : '') + '">' + I.wallet + 'ثبت تراکنش</button>' +
        '<button class="glass action press" data-toast="تحلیل بازار به‌زودی">' + I.bars + 'تحلیل بازار</button>' +
      '</div>' +

      '<div class="grid-2">' +
        '<article class="glass card stat down">' +
          '<div class="top"><h3>هزینه‌های این ماه</h3><span class="badge-ico">' + I.down + '</span></div>' +
          '<div class="val"><b class="num money">' + fa(a.expenses) + '</b><span>تومان</span></div>' +
          '<div class="foot"><span class="pill coral">' + (expChange <= 0 ? I.triDown : I.triUp) + ' ' + (expChange > 0 ? '+' : '') + pctT(expChange) + '</span> نسبت به ماه قبل</div>' +
          '<div class="bars" aria-hidden="true"><i style="height:26px"></i><i style="height:36px"></i><i style="height:48px"></i><i style="height:34px"></i><i style="height:44px"></i></div>' +
        '</article>' +
        '<article class="glass card stat up">' +
          '<div class="top"><h3>درآمد این ماه</h3><span class="badge-ico">' + I.up + '</span></div>' +
          '<div class="val"><b class="num money">' + fa(a.income) + '</b><span>تومان</span></div>' +
          '<div class="foot"><span class="pill mint">' + I.triUp + ' ' + (incChange >= 0 ? '+' : '') + pctT(incChange) + '</span> نسبت به ماه قبل</div>' +
          '<div class="bars" aria-hidden="true"><i style="height:22px"></i><i style="height:28px"></i><i style="height:36px"></i><i style="height:44px"></i><i style="height:52px"></i></div>' +
        '</article>' +
      '</div>' +

      '<div class="row-charts">' +
        '<article class="glass card donut-wrap">' +
          '<div class="card-head" style="margin:0"><h3 style="font-size:14px">توزیع دارایی‌ها</h3></div>' +
          '<div class="donut-body"><ul class="legend">' + parts.map((x) => '<li><i style="background:' + x.c + '"></i><span>' + x.label + (x.label === 'وجه نقد' || x.label === 'سایر' ? '' : ' <small>' + pct(x.v / tot) + '</small>') + '</span></li>').join('') + '</ul>' +
          '<svg viewBox="0 0 120 120" class="donut" aria-label="نمودار توزیع">' + segs + '</svg></div>' +
        '</article>' +
        '<article class="glass card">' +
          '<div class="card-head" style="margin-bottom:8px"><h3 style="font-size:14px">روند دارایی‌ها در ۶ ماه اخیر</h3></div>' +
          '<span class="chip-select">' + I.caret + ' ۶ ماه اخیر</span>' +
          '<svg class="trend-svg" viewBox="0 0 ' + tw + ' ' + th + '" aria-label="نمودار روند دارایی">' +
            '<defs><linearGradient id="areaG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2fd9a6" stop-opacity=".45"/><stop offset="1" stop-color="#2fd9a6" stop-opacity="0"/></linearGradient>' +
            '<linearGradient id="lineG" x1="0" x2="1"><stop offset="0" stop-color="#2fd9a6"/><stop offset=".5" stop-color="#1d77ac"/><stop offset="1" stop-color="#2fd9a6"/></linearGradient></defs>' +
            tp.map((q) => '<line x1="' + q[0] + '" x2="' + q[0] + '" y1="' + (y0 - 8) + '" y2="' + y1 + '" stroke="rgba(13,51,82,.07)"/>').join('') +
            '<path d="' + tPath + ' L' + x1 + ',' + y1 + ' L' + x0 + ',' + y1 + ' Z" fill="url(#areaG)"/>' +
            '<path d="' + tPath + '" fill="none" stroke="url(#lineG)" stroke-width="2.6" stroke-linecap="round"/>' +
            tp.map((q, i) => '<circle cx="' + q[0] + '" cy="' + q[1] + '" r="' + (i === tp.length - 1 ? 5 : 4) + '" fill="#fff" stroke="' + (i === tp.length - 1 ? '#12a37b' : '#2fd9a6') + '" stroke-width="2.4"/>').join('') +
            '<rect x="' + (tl[0] - 48) + '" y="' + (tl[1] - 34) + '" width="52" height="22" rx="11" fill="#0d3352"/>' +
            '<text x="' + (tl[0] - 22) + '" y="' + (tl[1] - 19) + '" text-anchor="middle" fill="#fff" font-size="11" font-weight="800">' + compact(a.netWorth) + '</text>' +
            months.map((m, i) => '<text x="' + tp[i][0] + '" y="' + (y1 + 22) + '" text-anchor="middle" fill="#2a3f55" font-size="10.5">' + jMonth(m) + '</text>').join('') +
          '</svg>' +
        '</article>' +
      '</div>' +

      '<article class="glass card">' +
        '<div class="card-head"><h2>آخرین تراکنش‌ها</h2><button class="link" data-go="achievements">مشاهده همه ' + I.arrowL + '</button></div>' +
        '<div class="tx"><span class="ico navy">' + I.brief + '</span><div class="meta">امروز<small>۱۴:۳۲</small></div><span class="amt num money">+' + fa(4000000) + '</span><div class="meta" style="text-align:left;flex:0 0 auto">دریافت حقوق<small>از شرکت</small></div><span class="ico mint" style="width:48px;height:48px">' + I.up + '</span></div>' +
      '</article>' +
    '</section>';
  }

  /* ================================================================== */
  /* View: Goals dashboard                                              */
  /* ================================================================== */

  function viewGoals() {
    const P = plan();
    const a = P.analysis, g = state.game;
    const lv = E.levelFromXp(g.xp);
    const streak = E.computeStreak(g.deposits, now());
    const ranked = P.ranked;
    const completed = state.goals.filter((x) => x.status === 'completed');

    let html = '<section class="view">' + topbar('اهداف من', 'home',
      '<button class="icon-btn" data-action="new-goal" aria-label="هدف جدید">' + I.plus + '</button>');

    // gamification strip
    html += '<article class="glass-dark game-strip press" data-go="achievements">' +
      '<div class="lvl-badge">' + faN(lv.level) + '</div>' +
      '<div class="info"><b>سطح ' + faN(lv.level) + ' · ' + lv.name + '</b><br><small>' + fa(lv.xp) + (lv.next ? ' / ' + fa(lv.next) : '') + ' XP · ' + faN(Object.keys(g.badges || {}).length) + ' نشان</small>' +
      '<div class="xpbar"><i style="width:' + (lv.progress * 100).toFixed(1) + '%"></i></div></div>' +
      '<div class="streak"><span class="flame">🔥</span>' + faN(streak) + '<small>هفته پیاپی</small></div>' +
      '</article>';

    if (!ranked.length) {
      html += '<article class="glass card empty"><div class="big">🎯</div><h3>هنوز هدفی نساختی</h3><p>هر چیزی که می‌خواهی بخری را به یک مسیر قابل اندازه‌گیری تبدیل کن.</p><button class="btn primary" data-action="new-goal">ساخت اولین هدف</button></article>';
    } else {
      // hero: most important goal
      const hg = ranked[0], hp = P.plans[hg.id];
      html += '<article class="glass-dark hero-goal">' +
        '<span class="tag">⭐ مهم‌ترین هدف</span>' +
        '<div class="body">' + ring(108, 11, hp.progress, goalVisual(hg) + '<b>' + pct(hp.progress) + '</b>', { dark: true }) +
          '<div style="flex:1;min-width:0"><h2>' + esc(hg.name) + '</h2>' +
          '<div class="money money"><b class="num">' + fa(hg.saved) + '</b> از ' + fa(hp.projectedTarget) + ' تومان</div>' +
          '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' + feasPill(hp) + (hp.schedule.behind ? '<span class="pill rtl coral">عقب از برنامه</span>' : '') + '</div></div>' +
        '</div>' +
        '<div class="kpis">' +
          '<div class="kpi"><small>ماهانه</small><b class="num">' + compact(hp.scenarios[hp.selected].monthly) + '</b></div>' +
          '<div class="kpi"><small>زمان باقی‌مانده</small><b>' + duration(hp.projectedMonths) + '</b></div>' +
          '<div class="kpi"><small>تاریخ رسیدن</small><b>' + jDate(hp.projectedDate) + '</b></div>' +
        '</div>' +
        '<div class="btn-row"><button class="btn primary" style="flex:1" data-action="deposit" data-id="' + hg.id + '">+ واریز</button>' +
        '<button class="btn ghost" style="flex:1" data-open="' + hg.id + '">مشاهده رودمپ</button></div>' +
        '</article>';

      // capacity / engine summary
      const totalA = P.totalAllocated;
      html += '<article class="glass capacity">' +
        '<div class="card-head" style="margin:0"><h3>ظرفیت پس‌انداز ماهانه</h3><b class="num">' + toman(a.capacity) + '</b></div>' +
        '<div class="stack-bar">' + ranked.map((x, i) => '<i title="' + esc(x.name) + '" style="width:' + (a.capacity ? P.plans[x.id].allocated / a.capacity * 100 : 0) + '%;background:' + GOAL_COLORS[i % GOAL_COLORS.length] + '"></i>').join('') + '</div>' +
        '<ul class="legend" style="grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">' + ranked.map((x, i) => '<li><i style="background:' + GOAL_COLORS[i % GOAL_COLORS.length] + '"></i><span>' + esc(x.name) + '</span><small class="num">' + compact(P.plans[x.id].allocated) + '</small></li>').join('') +
          (P.freeCapacity > 1000 ? '<li><i style="background:rgba(13,51,82,.1)"></i><span>آزاد</span><small>' + compact(P.freeCapacity) + '</small></li>' : '') + '</ul>' +
        '<div class="cap-row"><span class="sub">مازاد ماهانه: ' + toman(a.surplus) + '</span><span class="sub">بافر ایمنی ۲۰٪: ' + compact(a.bufferAmount) + '</span></div>' +
        '<div class="emergency"><span>🛡️ صندوق اضطراری</span><div class="bar"><i style="width:' + (a.emergencyRatio * 100).toFixed(0) + '%"></i></div><b>' + pct(a.emergencyRatio) + '</b></div>' +
        '</article>';

      if (P.totalDemand > a.capacity * 1.02) {
        html += '<article class="glass alert info"><span class="ico">🧭</span><div>مجموع نیاز ماهانه‌ی اهدافت <b>' + toman(P.totalDemand) + '</b> است و ظرفیت پایدارت <b>' + toman(a.capacity) + '</b>. اهداف بالاتر اول تأمین می‌شوند و با تکمیل هر هدف، سهمش خودکار به هدف بعدی می‌رسد.</div></article>';
      }

      // other goals
      if (ranked.length > 1) {
        html += '<div class="section-title"><h2>سایر اهداف</h2><span class="sub">ترتیب = اولویت</span></div>';
        ranked.slice(1).forEach((x, j) => {
          const i = j + 1, xp = P.plans[x.id];
          html += '<article class="glass goal-item press">' +
            '<div class="reorder"><button data-action="move" data-id="' + x.id + '" data-dir="-1" aria-label="بالاتر">' + I.chevUp + '</button>' +
            '<button data-action="move" data-id="' + x.id + '" data-dir="1" ' + (i === ranked.length - 1 ? 'disabled' : '') + ' aria-label="پایین‌تر">' + I.chevDown + '</button></div>' +
            '<div data-open="' + x.id + '" style="display:flex;align-items:center;gap:12px;flex:1;min-width:0;cursor:pointer">' +
            ring(64, 7, xp.progress, goalVisual(x).replace('class="emoji"', 'class="emoji" style="font-size:22px"'), { c1: GOAL_COLORS[i % GOAL_COLORS.length], c2: '#1d77ac' }) +
            '<div class="meta"><h3>' + esc(x.name) + '</h3>' +
              '<div class="line"><b class="num" style="color:var(--ink)">' + pct(xp.progress) + '</b><span>·</span><span>' + duration(xp.projectedMonths) + ' مانده</span></div>' +
              '<div class="line">' + feasPill(xp) + '<span class="pill rtl navy">اولویت ' + PRIORITY[x.priority] + '</span></div>' +
            '</div></div></article>';
        });
      }
    }

    if (completed.length) {
      html += '<div class="section-title"><h2>تکمیل‌شده‌ها 🏆</h2><button class="link sub" data-go="achievements">دستاوردها</button></div>';
      completed.forEach((x) => {
        html += '<article class="glass goal-item" style="opacity:.85"><span style="font-size:30px">' + esc(x.emoji || '🏆') + '</span><div class="meta"><h3>' + esc(x.name) + '</h3><div class="line">' + toman(x.saved) + ' · ' + jDate(x.completedAt) + '</div></div><span class="pill mint">✓</span></article>';
      });
    }
    html += '</section>';
    return html;
  }

  /* ================================================================== */
  /* View: Goal detail (analysis, scenarios, what-if, roadmap)          */
  /* ================================================================== */

  function viewGoal() {
    const goal = state.goals.find((x) => x.id === ui.goalId);
    if (!goal) { ui.view = 'goals'; return viewGoals(); }
    if (goal.status === 'completed') return viewCompletedGoal(goal);
    const P = plan();
    const p = P.plans[goal.id], a = P.analysis;
    const sel = p.scenarios[p.selected];

    let html = '<section class="view">' + topbar(esc(goal.name), 'goals',
      '<button class="icon-btn" data-action="edit-goal" data-id="' + goal.id + '" aria-label="ویرایش">' + I.edit + '</button>');

    html += '<article class="glass-dark detail-hero">' +
      ring(150, 14, p.progress, goalVisual(goal).replace('class="emoji"', 'class="emoji" style="font-size:44px"') + '<b style="font-size:20px">' + pct(p.progress) + '</b>', { dark: true }) +
      '<h2>' + esc(goal.name) + '</h2>' +
      '<div class="money"><b class="num">' + fa(goal.saved) + '</b> از ' + fa(p.projectedTarget) + ' تومان</div>' +
      '<div class="sub" style="color:rgba(255,255,255,.55);margin-top:4px">قیمت امروز ' + toman(p.currentTarget) + ' · تورم سالانه ' + pct(goal.inflation) + '</div>' +
      '<div class="chips">' + feasPill(p) + '<span class="pill rtl navy" style="background:rgba(255,255,255,.1);color:#fff">اولویت ' + PRIORITY[goal.priority] + '</span><span class="pill rtl navy" style="background:rgba(255,255,255,.1);color:#fff">' + sel.label + '</span></div>' +
      '</article>';

    // ---- alerts: schedule + suggestions + change log
    if (p.schedule.tracked && p.schedule.behind) {
      html += '<article class="glass alert warn"><span class="ico">⏰</span><div><b>از برنامه عقب افتادی.</b> طبق برنامه الان باید <b class="num">' + toman(p.schedule.expected) + '</b> داشتی؛ <b class="num">' + toman(Math.round(p.schedule.gap)) + '</b> فاصله داری. نگران نباش، دو راه داری:' +
        '<div class="actions-inline"><button class="btn sm primary" data-action="deposit" data-id="' + goal.id + '" data-amount="' + Math.round(p.schedule.gap) + '">واریز جبرانی</button>' +
        '<button class="btn sm light" data-action="rebaseline" data-id="' + goal.id + '">برنامه را از امروز به‌روز کن</button></div></div></article>';
    } else if (p.schedule.tracked && p.schedule.isAhead) {
      html += '<article class="glass alert good"><span class="ico">🚀</span><div><b>جلوتر از برنامه‌ای!</b> <span class="num">' + toman(Math.round(p.schedule.ahead)) + '</span> بیشتر از برنامه پس‌انداز کردی.</div></article>';
    }
    const extend = p.advice.find((t) => t.kind === 'extend');
    if (extend && extend.months > 0) {
      html += '<article class="glass alert info"><span class="ico">💡</span><div>با سهم فعلی، این هدف <b>' + duration(extend.months) + '</b> دیرتر از مهلتت (' + jDate(goal.deadline) + ') محقق می‌شود. برای رسیدن در مهلت، ماهانه <b class="num">' + toman(p.requiredMonthly) + '</b> لازم است.' +
        '<div class="actions-inline"><button class="btn sm light" data-action="extend" data-id="' + goal.id + '" data-months="' + extend.months + '">تمدید مهلت تا ' + jDate(extend.date) + '</button>' +
        (p.rankIndex > 0 ? '<button class="btn sm light" data-action="make-top" data-id="' + goal.id + '">مهم‌ترین هدفم کن</button>' : '') + '</div></div></article>';
    }
    p.advice.filter((t) => t.type === 'warn').forEach((t) => {
      html += '<article class="glass alert warn"><span class="ico">⚠️</span><div>' + t.text + '</div></article>';
    });
    if (p.cascade) {
      html += '<article class="glass alert good"><span class="ico">🔁</span><div>با تکمیل اهداف بالاتر، از <b>' + jDate(p.cascade.date) + '</b> سهم ماهانه‌ی این هدف تا <b class="num">' + toman(p.cascade.monthly) + '</b> بیشتر می‌شود؛ این در محاسبه‌ی تاریخ لحاظ شده.</div></article>';
    }

    // ---- KPIs
    html += '<article class="glass card"><div class="card-head"><h3>تحلیل هوشمند</h3><span class="sub">بر اساس وضعیت مالی واقعی</span></div>' +
      '<div class="kpi-grid">' +
        '<div class="kpi"><small>توان پس‌انداز پایدار تو</small><b class="num">' + toman(a.capacity) + '</b></div>' +
        '<div class="kpi"><small>مبلغ باقی‌مانده</small><b class="num">' + toman(Math.max(0, p.projectedTarget - goal.saved)) + '</b></div>' +
        '<div class="kpi"><small>با شرایط فعلی می‌رسی در</small><b>' + jDate(p.projectedDate) + '</b></div>' +
        '<div class="kpi"><small>ماهانه لازم برای مهلت (' + duration(p.monthsLeft) + ')</small><b class="num">' + toman(p.requiredMonthly) + '</b></div>' +
      '</div>' +
      '<p class="sub" style="margin:12px 2px 0;line-height:1.9">سهم فعلی این هدف از ظرفیتت: <b class="num" style="color:var(--ink)">' + toman(p.allocated) + '</b> در ماه. قیمت با تورم کالا رشد می‌کند و پس‌اندازت سود ' + pct(state.profile.savingsReturn || 0) + ' سالانه می‌گیرد.</p>' +
      '</article>';

    // ---- scenarios
    const keys = ['conservative', 'normal', 'fast'];
    const maxM = Math.max.apply(null, keys.map((k) => isFinite(p.scenarios[k].months) ? p.scenarios[k].months : 0)) || 1;
    html += '<article class="glass card"><div class="card-head"><h3>سناریوهای رسیدن</h3><span class="sub">یکی را انتخاب کن</span></div><div class="scenarios">' +
      keys.map((k) => {
        const s = p.scenarios[k];
        const tone = s.pressure.level === 'high' ? 'coral' : s.pressure.level === 'medium' ? 'amber' : 'mint';
        return '<button class="scenario ' + (p.selected === k ? 'on' : '') + '" data-action="scenario" data-id="' + goal.id + '" data-key="' + k + '">' +
          '<div class="ttl">' + s.label + '</div><div class="en">' + s.en + '</div>' +
          '<div class="m">' + duration(s.months) + '</div>' +
          '<div class="amt num">' + compact(s.monthly) + '/ماه</div>' +
          '<span class="pill rtl ' + tone + ' press">فشار ' + s.pressure.label + '</span></button>';
      }).join('') + '</div>' +
      '<div class="compare-bars">' + keys.map((k) => {
        const s = p.scenarios[k];
        const col = k === 'fast' ? '#2fd9a6' : k === 'normal' ? '#1d77ac' : '#9fb6c6';
        return '<div class="r"><span>' + s.label + '</span><div class="track"><i style="width:' + (isFinite(s.months) ? s.months / maxM * 100 : 100) + '%;background:' + col + '"></i></div><span class="sub">' + (s.date ? jDate(s.date) : '—') + '</span></div>';
      }).join('') + '</div>' +
      '<p class="sub" style="margin:10px 2px 0">فشار مالی = سهم این پس‌انداز از درآمد ماهانه (' + pct(sel.pressure.ofIncome) + ' در سناریوی انتخابی). مسیر سریع فقط از بافر ایمنی استفاده می‌کند، نه از هزینه‌های ضروری.</p>' +
      '</article>';

    // ---- what-if
    const w = ui.whatIf;
    html += '<article class="glass card whatif" id="whatif"><div class="card-head"><h3>اگر… چه می‌شود؟ 🤔</h3><button class="link sub" data-action="whatif-reset">بازنشانی</button></div>' +
      '<div class="slider-row"><label>ماهانه بیشتر پس‌انداز کنم <span class="num" id="wi-extra-l">' + toman(w.extra) + '</span></label>' +
      '<input type="range" min="0" max="5000000" step="100000" value="' + w.extra + '" data-wi="extra" aria-label="پس‌انداز اضافه ماهانه"></div>' +
      '<div class="slider-row"><label>درآمدم تغییر کند <span class="num" id="wi-income-l">' + (w.income > 0 ? '+' : '') + faN(w.income) + '%</span></label>' +
      '<input type="range" min="-30" max="50" step="5" value="' + w.income + '" data-wi="income" aria-label="تغییر درآمد"></div>' +
      '<div class="toggle"><div>استفاده از نقدینگی آزاد<small>' + toman(a.freeCash) + ' (بعد از کسر صندوق اضطراری)</small></div><label class="switch"><input type="checkbox" data-wi="lump" ' + (w.lump ? 'checked' : '') + '><span></span></label></div>' +
      '<div class="toggle"><div>نقد کردن ۲۵٪ سرمایه‌گذاری‌ها<small>' + toman(a.investUsable * 0.25) + ' — پس از کسر ریسک نوسان و هزینه‌ی نقدشوندگی</small></div><label class="switch"><input type="checkbox" data-wi="invest" ' + (w.invest ? 'checked' : '') + '><span></span></label></div>' +
      '<div class="whatif-result" id="wi-result"></div>' +
      '</article>';

    // ---- cadence
    html += '<article class="glass card"><div class="card-head"><h3>برنامه‌ی پس‌انداز</h3></div>' +
      '<div class="seg" role="tablist">' + [['daily', 'روزانه'], ['weekly', 'هفتگی'], ['monthly', 'ماهانه']].map((c) => '<button class="' + (ui.cadence === c[0] ? 'on' : '') + '" data-action="cadence" data-key="' + c[0] + '">' + c[1] + '</button>').join('') + '</div>' +
      '<div class="cadence"><div><span class="sub">' + ({ daily: 'هر روز کنار بگذار', weekly: 'هر هفته کنار بگذار', monthly: 'هر ماه کنار بگذار' })[ui.cadence] + '</span><br><b class="num">' + toman(p.cadence[ui.cadence]) + '</b></div><span style="font-size:34px">' + ({ daily: '☕', weekly: '🪙', monthly: '💰' })[ui.cadence] + '</span></div>' +
      '</article>';

    // ---- 3D roadmap
    html += road3d(goal, p);

    // ---- roadmap
    const cur = p.milestones.find((m) => m.status === 'current');
    html += '<article class="glass card"><div class="card-head"><h3>رودمپ اختصاصی 🗺️</h3><span class="sub">' + (cur ? 'مرحله بعد: ' + faN(cur.pct) + '٪' : 'همه مراحل انجام شد') + '</span></div>' +
      '<div class="roadmap" id="roadmap"><div class="fill" id="rm-fill" style="height:0"></div>' +
      p.milestones.map((m) => '<div class="ms ' + m.status + '" data-amount="' + m.amount + '">' +
        '<div class="node">' + (m.status === 'done' ? '✓' : faN(m.pct) + '٪') + '</div>' +
        '<div class="box glass"><div class="t"><h4><bdi>' + faN(m.pct) + '٪</bdi> · ' + m.title + '</h4><span class="reward">⭐ ' + faN(m.xp) + ' XP' + (m.badge ? ' + ' + E.BADGES[m.badge].icon : '') + '</span></div>' +
        '<div class="d"><span>مبلغ: <b class="num">' + compact(m.amount) + '</b></span><span>تاریخ: <b>' + (m.status === 'done' ? 'انجام شد' : jDate(m.date)) + '</b></span>' +
        '<span>وضعیت: <b>' + ({ done: 'تکمیل ✓', current: 'در جریان', upcoming: 'در انتظار' })[m.status] + '</b></span>' +
        '<span>' + (m.status === 'done' ? '' : 'مانده: <b class="num">' + compact(m.remaining) + '</b>') + '</span></div></div></div>').join('') +
      '</div></article>';

    // ---- resources (investments are not cash)
    html += '<article class="glass card resources"><div class="card-head"><h3>منابع در دسترس</h3><span class="sub">سرمایه‌گذاری ≠ پول نقد</span></div>' +
      '<div class="r"><div>نقدینگی آزاد<small>موجودی نقد − پس‌انداز اهداف − صندوق اضطراری</small></div><b class="num">' + compact(a.freeCash) + '</b></div>' +
      a.investments.map((i) => '<div class="r"><div>' + esc(i.name) + '<small>نقدشوندگی ' + pct(i.liquidity) + ' · کسر ریسک ' + pct(i.volatility) + '</small></div><div style="text-align:left"><b class="num">' + compact(i.usable) + '</b><small class="sub num" style="display:block;text-decoration:line-through">' + compact(i.value) + '</small></div></div>').join('') +
      '</article>';

    // ---- change log (dynamic roadmap)
    if (goal.changes && goal.changes.length) {
      html += '<article class="glass card"><div class="card-head"><h3>تغییرات رودمپ</h3><span class="sub">اهدافت بدون اجازه‌ات عوض نمی‌شوند</span></div><ul class="changes">' +
        goal.changes.slice(0, 4).map(changeHtml).join('') + '</ul></article>';
    }

    html += '<div style="display:flex;gap:10px;margin:6px 0 90px"><button class="btn danger block" data-action="complete-goal" data-id="' + goal.id + '">خریدمش! 🎉</button><button class="btn danger block" data-action="delete-goal" data-id="' + goal.id + '">' + I.trash + ' حذف</button></div>';
    html += '</section>';
    return html;
  }

  /* 3D roadmap: a winding path on a tilted plane, milestone pins stand upright */
  function road3d(goal, p) {
    const pts = [[150, 400], [70, 330], [235, 258], [70, 182], [228, 108], [150, 34]];
    const ms = p.milestones;
    let done = 0, f = 0;
    for (let i = 0; i < ms.length; i++) {
      if (ms[i].status === 'done') { done = i + 1; continue; }
      const prev = i ? ms[i - 1].amount : 0;
      f = Math.max(0, Math.min(1, (goal.saved - prev) / (ms[i].amount - prev || 1)));
      break;
    }
    const prog = Math.min(1, (done + f) / ms.length) * 100;
    const d = smoothPath(pts);
    const pins = ms.map((m, i) => {
      const q = pts[i + 1];
      return '<div class="pin ' + m.status + '" style="left:' + q[0] + 'px;top:' + q[1] + 'px">' +
        '<div class="pin-up"><span class="orb">' + (m.pct === 100 ? goalVisual(goal) : (m.status === 'done' ? '✓' : faN(m.pct) + '٪')) + '</span>' +
        '<span class="lbl">' + (m.status === 'done' ? 'انجام شد' : jDate(m.date)) + '</span></div><i class="shadow"></i></div>';
    }).join('');
    return '<article class="glass-dark card road3d-card"><div class="card-head"><h3 style="color:#fff">رودمپ سه‌بعدی 🧭</h3><span class="sub" style="color:rgba(255,255,255,.6)">' + pct(p.progress) + ' از مسیر</span></div>' +
      '<div class="road3d"><div class="plane">' +
      '<svg width="300" height="430" viewBox="0 0 300 430"><defs><linearGradient id="r3g" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#2fd9a6"/><stop offset="1" stop-color="#5ff0c4"/></linearGradient></defs>' +
      '<path d="' + d + '" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="30" stroke-linecap="round"/>' +
      '<path d="' + d + '" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="2" stroke-dasharray="6 9" stroke-linecap="round"/>' +
      '<path class="road-prog" d="' + d + '" pathLength="100" fill="none" stroke="url(#r3g)" stroke-width="12" stroke-linecap="round" stroke-dasharray="' + prog.toFixed(1) + ' 100"/>' +
      '<circle cx="150" cy="400" r="10" fill="#2fd9a6"/></svg>' + pins +
      '<div class="pin start" style="left:150px;top:400px"><div class="pin-up"><span class="lbl">شروع</span></div></div>' +
      '</div></div></article>';
  }

  function viewCompletedGoal(goal) {
    return '<section class="view">' + topbar(esc(goal.name), 'goals') +
      '<article class="glass-dark detail-hero"><span style="font-size:70px">' + esc(goal.emoji || '🏆') + '</span><h2>' + esc(goal.name) + '</h2>' +
      '<div class="money">هدف کامل شد · ' + jDate(goal.completedAt) + '</div><div class="chips"><span class="pill solid-mint">🏆 ' + toman(goal.saved) + '</span></div></article>' +
      '<article class="glass card"><p style="margin:0;line-height:2">تبریک! این هدف در بخش دستاوردها ذخیره شد. پول آن را خرج خرید کن و سهمش از ظرفیت ماهانه، خودکار به هدف‌های بعدی رسید.</p></article></section>';
  }

  const REASON_TEXT = {
    income: (d) => 'درآمد ماهانه ' + fa(Math.abs(d)) + ' تومان ' + (d > 0 ? 'افزایش' : 'کاهش') + ' یافت',
    expenses: (d) => 'هزینه‌های ماهانه ' + fa(Math.abs(d)) + ' تومان ' + (d > 0 ? 'بیشتر' : 'کمتر') + ' شد',
    cash: (d) => 'موجودی نقد ' + fa(Math.abs(d)) + ' تومان ' + (d > 0 ? 'بیشتر' : 'کمتر') + ' شد',
    investments: (d) => 'سرمایه‌گذاری‌ها ' + fa(Math.abs(d)) + ' تومان ' + (d > 0 ? 'سود' : 'زیان') + ' داشتند',
    debts: (d) => 'قسط ماهانه ' + fa(Math.abs(d)) + ' تومان ' + (d > 0 ? 'اضافه' : 'کم') + ' شد',
    emergency: (d) => 'مدت صندوق اضطراری ' + (d > 0 ? 'بیشتر' : 'کمتر') + ' شد',
    return: (d) => 'سود سپرده ' + (d > 0 ? 'بیشتر' : 'کمتر') + ' شد',
    edit: () => 'هدف را ویرایش کردی',
    deadline: () => 'مهلت هدف را تمدید کردی',
    priority: () => 'اولویت اهداف را تغییر دادی',
    scenario: () => 'سناریوی جدید انتخاب کردی',
  };

  function changeHtml(c) {
    const lines = c.changes.map((x) => {
      if (x.kind === 'time') {
        if (!isFinite(x.delta)) return x.delta < 0 ? 'هدف دوباره قابل‌دستیابی شد (' + jDate(x.to) + ')' : 'با شرایط جدید تاریخ رسیدن نامشخص شد';
        return x.delta < 0 ? '🟢 ' + duration(-x.delta) + ' زودتر می‌رسی (' + jDate(x.to) + ')' : '🟠 ' + duration(x.delta) + ' دیرتر می‌رسی (' + jDate(x.to) + ')';
      }
      if (x.kind === 'monthly') return 'سهم ماهانه از ' + compact(x.from) + ' به ' + compact(x.to) + ' رسید';
      if (x.kind === 'feasibility') return 'وضعیت: ' + E.FEASIBILITY[x.from].label + ' ← ' + E.FEASIBILITY[x.to].label;
      return '';
    });
    const why = (c.reasons || []).map((r) => (REASON_TEXT[r.key] || (() => ''))(r.delta)).filter(Boolean).join('، ');
    return '<li>' + lines.join('<br>') + (why ? '<small>چون ' + why + ' · ' + jDay(c.date) + '</small>' : '<small>' + jDay(c.date) + '</small>') + '</li>';
  }

  /* ================================================================== */
  /* View: Achievements / reports                                       */
  /* ================================================================== */

  function viewAchievements() {
    const g = state.game, lv = E.levelFromXp(g.xp);
    const streak = E.computeStreak(g.deposits, now());
    const done = state.goals.filter((x) => x.status === 'completed');
    const totalSaved = g.deposits.reduce((s, d) => s + d.amount, 0);
    const goalName = (id) => { const x = state.goals.find((y) => y.id === id); return x ? x.name : 'هدف حذف‌شده'; };

    const hist = (g.history || []).slice(0, 15).map((h) => {
      let ico = '🪙', txt = '';
      if (h.type === 'deposit') { txt = 'واریز ' + toman(h.amount) + ' برای ' + esc(goalName(h.goalId)) + (h.xp ? ' · +' + faN(h.xp) + ' XP' : ''); }
      if (h.type === 'milestone') { ico = '📍'; txt = 'رسیدن به ' + faN(h.pct) + '٪ ' + esc(goalName(h.goalId)) + ' · +' + faN(h.xp) + ' XP'; }
      if (h.type === 'badge') { ico = E.BADGES[h.badge] ? E.BADGES[h.badge].icon : '🏅'; txt = 'نشان «' + (E.BADGES[h.badge] ? E.BADGES[h.badge].title : h.badge) + '» باز شد'; }
      if (h.type === 'complete') { ico = '🏆'; txt = esc(goalName(h.goalId)) + ' کامل شد'; }
      if (h.type === 'goal') { ico = '🎯'; txt = 'هدف ' + esc(goalName(h.goalId)) + ' ساخته شد'; }
      if (h.type === 'replan') { ico = '🗺️'; txt = 'برنامه‌ی ' + esc(goalName(h.goalId)) + ' به‌روز شد'; }
      return '<li><span class="hi">' + ico + '</span><div class="txt">' + txt + '<br><small>' + jDay(h.date) + '</small></div></li>';
    }).join('');

    return '<section class="view">' + topbar('گزارش و دستاوردها', 'home') +
      '<article class="glass-dark level-card"><div class="lvl-badge">' + faN(lv.level) + '</div><h2>سطح ' + faN(lv.level) + ' · ' + lv.name + '</h2>' +
      '<div class="sub" style="color:rgba(255,255,255,.65);margin-top:6px">' + (lv.next ? fa(lv.next - lv.xp) + ' XP تا سطح بعد' : 'بالاترین سطح!') + '</div>' +
      '<div class="xpbar"><i style="width:' + (lv.progress * 100).toFixed(1) + '%"></i></div>' +
      '<div class="stats"><div class="kpi"><small>امتیاز</small><b>' + fa(lv.xp) + ' XP</b></div><div class="kpi"><small>استریک</small><b>🔥 ' + faN(streak) + ' هفته</b></div><div class="kpi"><small>اهداف کامل</small><b>' + faN(done.length) + '</b></div></div>' +
      '</article>' +
      '<article class="glass card"><div class="card-head"><h3>نشان‌ها</h3><span class="sub">' + faN(Object.keys(g.badges || {}).length) + ' از ' + faN(Object.keys(E.BADGES).length) + '</span></div><div class="badges">' +
      Object.keys(E.BADGES).map((id) => { const b = E.BADGES[id], has = g.badges && g.badges[id]; return '<div class="badge glass ' + (has ? '' : 'locked') + '"><span class="i">' + (has ? b.icon : '🔒') + '</span><b>' + b.title + '</b><small>' + b.desc + '</small></div>'; }).join('') +
      '</div></article>' +
      '<article class="glass card"><div class="card-head"><h3>خلاصه</h3></div><div class="kpi-grid">' +
      '<div class="kpi"><small>کل پس‌انداز ثبت‌شده</small><b class="num">' + toman(totalSaved) + '</b></div>' +
      '<div class="kpi"><small>تعداد واریزها</small><b>' + faN(g.deposits.length) + '</b></div></div>' +
      '<p class="sub" style="margin:12px 2px 0;line-height:1.9">امتیاز برای <b>استمرار</b> داده می‌شود، نه مبلغ: یک واریز معقول در هفته همان‌قدر XP دارد که یک واریز بزرگ. هزینه‌های ضروری و صندوق اضطراری‌ات را فدای امتیاز نکن.</p></article>' +
      (done.length ? '<article class="glass card"><div class="card-head"><h3>اهداف تکمیل‌شده 🏆</h3></div>' + done.map((x) => '<div class="tx"><span class="ico mint" style="font-size:24px">' + esc(x.emoji || '🏆') + '</span><div class="meta">' + esc(x.name) + '<small>' + jDate(x.completedAt) + '</small></div><b class="num">' + compact(x.saved) + '</b></div>').join('') + '</article>' : '') +
      '<article class="glass card"><div class="card-head"><h3>تاریخچه</h3></div><ul class="history">' + (hist || '<li>هنوز چیزی ثبت نشده</li>') + '</ul></article>' +
      '</section>';
  }

  /* ================================================================== */
  /* View: Assets / financial status (drives the dynamic roadmap)       */
  /* ================================================================== */

  function viewAssets() {
    const p = state.profile, a = plan().analysis;
    const money = (k, label, hint) => '<div class="field"><label>' + label + '</label><div class="input-suffix"><input class="input money" inputmode="numeric" data-pf="' + k + '" value="' + fa(p[k]) + '"><span>تومان</span></div>' + (hint ? '<div class="hint">' + hint + '</div>' : '') + '</div>';
    const typeOpts = (sel) => Object.keys(E.ASSET_RULES).map((k) => '<option value="' + k + '" ' + (k === sel ? 'selected' : '') + '>' + E.ASSET_RULES[k].label + '</option>').join('');

    return '<section class="view">' + topbar('وضعیت مالی', 'home') +
      '<article class="glass-dark card"><div class="kpi-grid">' +
        '<div class="kpi"><small>مازاد ماهانه</small><b class="num">' + toman(a.surplus) + '</b></div>' +
        '<div class="kpi"><small>ظرفیت پایدار برای اهداف</small><b class="num">' + toman(a.capacity) + '</b></div>' +
        '<div class="kpi"><small>صندوق اضطراری</small><b>' + pct(a.emergencyRatio) + ' از ' + compact(a.emergencyTarget) + '</b></div>' +
        '<div class="kpi"><small>نرخ پس‌انداز</small><b>' + pct(a.savingsRate) + '</b></div>' +
      '</div></article>' +
      '<article class="glass card"><div class="card-head"><h3>شبیه‌سازی رویداد</h3><span class="sub">برای تست رودمپ پویا</span></div>' +
        '<div class="quick-amts" style="margin:0"><button data-action="sim" data-key="raise">💼 افزایش حقوق ۱۵٪</button><button data-action="sim" data-key="cost">🧾 هزینه ثابت +۴۰۰ هزار</button><button data-action="sim" data-key="gain">📈 سود سرمایه‌گذاری ۱۰٪</button><button data-action="sim" data-key="loss">📉 زیان سرمایه‌گذاری ۱۵٪</button></div>' +
        '<p class="sub" style="margin:10px 2px 0">هر تغییری را ذخیره کنی، همه‌ی رودمپ‌ها دوباره محاسبه می‌شوند و دلیل تغییر برایت نوشته می‌شود.</p></article>' +
      '<form class="glass card" id="profile-form"><div class="card-head"><h3>درآمد و هزینه</h3></div>' +
        money('monthlyIncome', 'درآمد ماهانه') +
        '<div class="row-2">' + money('fixedExpenses', 'هزینه ثابت') + money('variableExpenses', 'هزینه متغیر') + '</div>' +
        money('cash', 'موجودی نقد', 'شامل پولی که برای اهداف کنار گذاشته‌ای (' + compact(a.earmarked) + ')') +
        '<div class="row-2"><div class="field"><label>صندوق اضطراری (ماه)</label><input class="input" type="number" min="0" max="12" data-pf="emergencyMonths" value="' + p.emergencyMonths + '"></div>' +
        '<div class="field"><label>سود سالانه سپرده (٪)</label><input class="input" type="number" min="0" max="60" data-pf="savingsReturn" value="' + Math.round((p.savingsReturn || 0) * 100) + '"></div></div>' +
        '<div class="card-head" style="margin-top:6px"><h3>سرمایه‌گذاری‌ها</h3><button type="button" class="link sub" data-action="add-inv">+ افزودن</button></div>' +
        '<div id="inv-list">' + p.investments.map((i) => '<div class="inv-row" data-inv="' + esc(i.id) + '"><input class="input" data-k="name" value="' + esc(i.name) + '"><select class="input" data-k="type">' + typeOpts(i.type) + '</select><input class="input money" inputmode="numeric" data-k="value" value="' + fa(i.value) + '"><button type="button" data-action="rm-row">×</button></div>').join('') + '</div>' +
        '<div class="card-head" style="margin-top:6px"><h3>بدهی‌ها و اقساط</h3><button type="button" class="link sub" data-action="add-debt">+ افزودن</button></div>' +
        '<div id="debt-list">' + (p.debts || []).map((d) => '<div class="inv-row" data-debt="' + esc(d.id) + '"><input class="input" data-k="name" value="' + esc(d.name) + '" placeholder="عنوان"><input class="input money" inputmode="numeric" data-k="monthlyPayment" value="' + fa(d.monthlyPayment) + '" placeholder="قسط ماهانه"><input class="input money" inputmode="numeric" data-k="balance" value="' + fa(d.balance) + '" placeholder="مانده"><button type="button" data-action="rm-row">×</button></div>').join('') + '</div>' +
        '<button class="btn primary block" type="submit" style="margin-top:8px">ذخیره و محاسبه دوباره</button>' +
      '</form></section>';
  }

  /* ================================================================== */
  /* Overlays: sheets, celebration                                      */
  /* ================================================================== */

  const slot = document.getElementById('overlay-slot');

  function openSheet(inner, onMount) {
    slot.innerHTML = '<div class="sheet-backdrop" data-action="close-sheet"></div><div class="sheet" role="dialog" aria-modal="true"><div class="grab"></div>' + inner + '</div>';
    const bd = slot.querySelector('.sheet-backdrop'), sh = slot.querySelector('.sheet');
    requestAnimationFrame(() => { bd.classList.add('open'); sh.classList.add('open'); });
    if (onMount) onMount(sh);
  }
  function closeSheet() {
    const bd = slot.querySelector('.sheet-backdrop'), sh = slot.querySelector('.sheet');
    if (!sh) return;
    bd.classList.remove('open'); sh.classList.remove('open');
    setTimeout(() => { if (slot.querySelector('.sheet') === sh) slot.innerHTML = ''; }, 380);
  }

  /* ---------- goal create / edit ---------- */
  function goalForm(goal) {
    const isNew = !goal;
    const t = now();
    const g = goal || { name: '', emoji: '🎮', image: null, price: 0, saved: 0, priority: 'medium', inflation: 0.15, deadline: E.addMonths(t, 12).toISOString() };
    const curMonths = Math.max(1, E.monthsBetween(t, g.deadline));
    const opts = [];
    for (let m = 1; m <= 120; m++) opts.push('<option value="' + m + '" ' + (m === curMonths ? 'selected' : '') + '>' + jDate(E.addMonths(t, m)) + ' (' + durationT(m) + ')</option>');
    const infl = [0, 0.1, 0.15, 0.25, 0.35, 0.45];
    if (infl.indexOf(g.inflation) === -1) infl.push(g.inflation);

    openSheet(
      '<h2>' + (isNew ? 'هدف جدید ✨' : 'ویرایش هدف') + '</h2><form id="goal-form">' +
      '<div class="field"><label>چی می‌خوای؟</label><input class="input" name="name" required maxlength="40" placeholder="مثلاً PlayStation 5" value="' + esc(g.name) + '"></div>' +
      '<div class="field"><label>تصویر هدف</label><div class="emoji-pick" id="emoji-pick">' +
        EMOJIS.map((e) => '<button type="button" data-emoji="' + e + '" class="' + (!g.image && g.emoji === e ? 'on' : '') + '">' + e + '</button>').join('') +
        '<button type="button" class="upload ' + (g.image ? 'on' : '') + '" data-action="pick-image">' + (g.image ? '<img src="' + esc(g.image) + '" style="width:30px;height:30px;border-radius:8px;object-fit:cover">' : '📷 آپلود') + '</button>' +
        '<input type="file" accept="image/*" id="img-input" hidden></div></div>' +
      '<div class="row-2"><div class="field"><label>قیمت امروز</label><input class="input money" name="price" inputmode="numeric" required value="' + (g.price ? fa(g.price) : '') + '" placeholder="۰"></div>' +
      '<div class="field"><label>کنار گذاشته‌شده</label><input class="input money" name="saved" inputmode="numeric" value="' + (g.saved ? fa(g.saved) : '') + '" placeholder="۰"></div></div>' +
      '<div class="field"><label>کِی می‌خوای بهش برسی؟</label><select class="input" name="months">' + opts.join('') + '</select></div>' +
      '<div class="field"><label>اهمیت و اولویت</label><div class="seg" id="prio-seg">' + ['high', 'medium', 'low'].map((k) => '<button type="button" data-prio="' + k + '" class="' + (g.priority === k ? 'on' : '') + '">' + PRIORITY[k] + '</button>').join('') + '</div></div>' +
      '<div class="field"><label>رشد سالانه قیمت این کالا</label><select class="input" name="inflation">' + infl.sort((x, y) => x - y).map((v) => '<option value="' + v + '" ' + (v === g.inflation ? 'selected' : '') + '>' + pctT(v) + (v === 0 ? ' (قیمت ثابت)' : '') + '</option>').join('') + '</select><div class="hint">قیمت کالا تا روز خرید با این نرخ گران‌تر حساب می‌شود.</div></div>' +
      '<div class="preview-box" id="goal-preview">مبلغ را وارد کن تا موتور هوشمند مسیرت را حساب کند…</div>' +
      '<button class="btn primary block" type="submit">' + (isNew ? 'ساخت هدف و رودمپ' : 'ذخیره تغییرات') + '</button></form>',
      (sh) => {
        const form = sh.querySelector('#goal-form');
        const st = { emoji: g.emoji, image: g.image, priority: g.priority };
        const read = () => ({
          name: form.name.value.trim(), price: parseMoney(form.price.value), saved: parseMoney(form.saved.value),
          months: +form.months.value, inflation: +form.inflation.value,
        });
        const preview = () => {
          const v = read();
          const box = sh.querySelector('#goal-preview');
          if (!v.price) { box.innerHTML = 'مبلغ را وارد کن تا موتور هوشمند مسیرت را حساب کند…'; return; }
          const draft = buildGoal(goal, v, st, true);
          const others = state.goals.filter((x) => !goal || x.id !== goal.id);
          const P = E.planAll(state.profile, others.concat([draft]), now());
          const p = P.plans[draft.id];
          if (!p) { box.innerHTML = 'این مبلغ را همین حالا داری! 🎉'; return; }
          box.innerHTML = 'قیمت در روز خرید: <b class="num">' + toman(p.deadlineTarget) + '</b><br>' +
            'برای رسیدن در مهلت: ماهانه <b class="num">' + toman(p.requiredMonthly) + '</b> (هفته‌ای ' + compact(p.requiredMonthly * 12 / 52) + ')<br>' +
            'با شرایط فعلی می‌رسی: <b>' + jDate(p.projectedDate) + '</b><br>وضعیت: ' + feasPill(p);
        };
        form.addEventListener('input', (e) => {
          if (e.target.classList.contains('money')) liveMoney(e.target);
          preview();
        });
        form.addEventListener('change', preview);
        sh.querySelector('#emoji-pick').addEventListener('click', (e) => {
          const b = e.target.closest('button'); if (!b) return;
          if (b.dataset.action === 'pick-image') { sh.querySelector('#img-input').click(); return; }
          st.emoji = b.dataset.emoji; st.image = null;
          sh.querySelectorAll('#emoji-pick button').forEach((x) => x.classList.toggle('on', x === b));
        });
        sh.querySelector('#img-input').addEventListener('change', (e) => {
          const f = e.target.files && e.target.files[0]; if (!f) return;
          resizeImage(f, 256).then((url) => {
            st.image = url;
            sh.querySelectorAll('#emoji-pick button').forEach((x) => x.classList.remove('on'));
            const up = sh.querySelector('.upload'); up.classList.add('on');
            up.innerHTML = '<img src="' + url + '" style="width:30px;height:30px;border-radius:8px;object-fit:cover">';
          });
        });
        sh.querySelector('#prio-seg').addEventListener('click', (e) => {
          const b = e.target.closest('button'); if (!b) return;
          st.priority = b.dataset.prio;
          sh.querySelectorAll('#prio-seg button').forEach((x) => x.classList.toggle('on', x === b));
          preview();
        });
        form.addEventListener('submit', (e) => {
          e.preventDefault();
          const v = read();
          if (!v.name || !v.price) { toast('نام و قیمت هدف را وارد کن'); return; }
          if (v.saved > v.price) v.saved = v.price;
          if (isNew) createGoal(v, st); else updateGoal(goal, v, st);
          closeSheet();
        });
        preview();
      }
    );
  }

  function buildGoal(goal, v, st, draft) {
    const t = now();
    return Object.assign({}, goal || {}, {
      id: goal ? goal.id : (draft ? '__draft' : uid()),
      name: v.name || 'هدف جدید', emoji: st.emoji, image: st.image,
      price: v.price, priceDate: goal && goal.price === v.price ? goal.priceDate : t.toISOString(),
      inflation: v.inflation, saved: v.saved, deadline: E.addMonths(t, v.months).toISOString(),
      priority: st.priority, status: 'active',
      rank: goal ? goal.rank : (st.priority === 'high' ? -1 : 999),
      scenario: goal ? goal.scenario : 'normal',
      createdAt: goal ? goal.createdAt : t.toISOString(),
      reachedMilestones: goal ? goal.reachedMilestones : [],
      changes: goal ? goal.changes : [],
      baseline: goal ? goal.baseline : null,
    });
  }

  function normalizeRanks() {
    state.goals.filter((g) => g.status !== 'completed').sort((a, b) => a.rank - b.rank).forEach((g, i) => { g.rank = i; });
  }

  function createGoal(v, st) {
    const t = now();
    const g = buildGoal(null, v, st);
    // new money set aside counts as cash the user already has
    state.goals.push(g);
    normalizeRanks();
    const P = plan();
    const p = P.plans[g.id];
    g.baseline = { date: t.toISOString(), saved: g.saved, monthly: p ? p.scenarios.normal.monthly : 0 };
    state.game.xp += 30;
    E.logHistory(state.game, t, 'goal', { goalId: g.id });
    const active = state.goals.filter((x) => x.status !== 'completed').length;
    const badges = E.grantBadges(state.game, ['first_goal'].concat(active >= 3 ? ['multi_goal'] : []), t);
    save();
    ui.view = 'goal'; ui.goalId = g.id; resetWhatIf();
    render();
    if (badges.length) celebrate({ title: 'هدف ساخته شد!', text: 'رودمپ اختصاصی «' + g.name + '» آماده است.', xp: 30, badges, emoji: g.emoji });
    else toast('🎯 هدف ساخته شد · +۳۰ XP');
  }

  function updateGoal(goal, v, st) {
    const before = plan();
    Object.assign(goal, buildGoal(goal, v, st));
    normalizeRanks();
    recordReplan(before, [{ key: 'edit' }], goal.id);
    save(); render(); toast('تغییرات ذخیره و رودمپ دوباره محاسبه شد');
  }

  /** Store explanations for every goal whose plan changed. */
  function recordReplan(before, reasons, onlyId) {
    const after = plan();
    const diff = E.diffPlans(before, after, reasons);
    let n = 0;
    Object.keys(diff).forEach((id) => {
      if (onlyId && id !== onlyId && reasons[0].key === 'edit') return;
      const g = state.goals.find((x) => x.id === id);
      if (!g) return;
      g.changes = g.changes || [];
      g.changes.unshift({
        date: now().toISOString(), reasons,
        changes: diff[id].changes.map((c) => Object.assign({}, c, { from: c.from instanceof Date ? c.from.toISOString() : c.from, to: c.to instanceof Date ? c.to.toISOString() : c.to })),
      });
      g.changes.length = Math.min(g.changes.length, 10);
      n++;
    });
    return n;
  }

  function resizeImage(file, max) {
    return new Promise((resolve) => {
      const r = new FileReader();
      r.onload = () => {
        const img = new Image();
        img.onload = () => {
          const s = Math.min(1, max / Math.max(img.width, img.height));
          const c = document.createElement('canvas');
          c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          resolve(c.toDataURL('image/jpeg', 0.82));
        };
        img.src = r.result;
      };
      r.readAsDataURL(file);
    });
  }

  /* ---------- deposit ---------- */
  function depositSheet(goalId, preset) {
    const active = plan();
    if (!active.ranked.length) { toast('اول یک هدف بساز'); ui.view = 'goals'; render(); return; }
    const id = goalId && active.plans[goalId] ? goalId : active.ranked[0].id;
    const a = active.analysis;
    const t = now();
    const monthDeps = state.game.deposits.filter((d) => { const x = new Date(d.date); return x.getMonth() === t.getMonth() && x.getFullYear() === t.getFullYear(); }).reduce((s, d) => s + d.amount, 0);

    openSheet(
      '<h2>واریز به هدف 🪙</h2><form id="dep-form">' +
      '<div class="field"><label>کدام هدف؟</label><select class="input" name="goal">' + active.ranked.map((g) => '<option value="' + g.id + '" ' + (g.id === id ? 'selected' : '') + '>' + esc((g.emoji || '') + ' ' + g.name) + '</option>').join('') + '</select></div>' +
      '<div class="field"><label>مبلغ</label><div class="input-suffix"><input class="input money" name="amount" inputmode="numeric" required value="' + (preset ? fa(preset) : '') + '" placeholder="۰"><span>تومان</span></div>' +
      '<div class="quick-amts" id="quick"></div></div>' +
      '<div class="preview-box">مازاد این ماه: <b class="num">' + toman(a.surplus) + '</b><br>واریزهای این ماه تا الان: <b class="num">' + toman(monthDeps) + '</b><br><span class="sub">امتیاز برای استمرار است؛ لازم نیست بیشتر از توانت واریز کنی.</span></div>' +
      '<button class="btn primary block" type="submit">ثبت واریز</button></form>',
      (sh) => {
        const form = sh.querySelector('#dep-form');
        const quick = () => {
          const p = active.plans[form.goal.value];
          const items = [['هفتگی', p.cadence.weekly], ['ماهانه', p.cadence.monthly]];
          if (p.schedule.behind) items.push(['جبران عقب‌ماندگی', p.schedule.gap]);
          const next = p.milestones.find((m) => m.status === 'current');
          if (next && next.remaining > 0) items.push(['تا ' + faN(next.pct) + '٪', next.remaining]);
          sh.querySelector('#quick').innerHTML = items.map((x) => '<button type="button" data-v="' + Math.ceil(x[1] / 1000) * 1000 + '">' + x[0] + ' · ' + compact(Math.ceil(x[1] / 1000) * 1000) + '</button>').join('');
        };
        quick();
        form.goal.addEventListener('change', quick);
        sh.querySelector('#quick').addEventListener('click', (e) => {
          const b = e.target.closest('button'); if (!b) return;
          form.amount.value = fa(+b.dataset.v);
        });
        form.amount.addEventListener('input', () => liveMoney(form.amount));
        form.addEventListener('submit', (e) => {
          e.preventDefault();
          const amount = parseMoney(form.amount.value);
          if (!amount) { toast('مبلغ را وارد کن'); return; }
          const gid = form.goal.value;
          const ev = E.applyDeposit(state, gid, amount, now());
          save();
          closeSheet();
          render();
          const goal = state.goals.find((g) => g.id === gid);
          if (ev.milestones.length || ev.badges.length || ev.levelUp || ev.completed) {
            const m = ev.milestones[ev.milestones.length - 1];
            celebrate({
              title: ev.completed ? 'به هدفت رسیدی! 🏆' : m ? 'نقطه عطف ' + faN(m.pct) + '٪!' : ev.levelUp ? 'سطح جدید!' : 'نشان جدید!',
              text: ev.completed ? '«' + goal.name + '» کامل شد. وقت خریدشه!' : m ? m.title + ' — «' + goal.name + '»' : ev.levelUp ? 'به سطح ' + faN(ev.levelUp.level) + ' (' + ev.levelUp.name + ') رسیدی' : 'ادامه بده، داری عالی پیش می‌ری',
              xp: ev.xp, badges: ev.badges, emoji: ev.completed ? '🏆' : goal.emoji, warnings: ev.warnings,
            });
          } else {
            toast('✅ ' + toman(amount) + ' ثبت شد' + (ev.xp ? ' · +' + faN(ev.xp) + ' XP' : '') + (ev.warnings.length ? ' — ⚠️ ' + ev.warnings[0] : ''));
          }
        });
      }
    );
  }

  /* ---------- more menu ---------- */
  function moreSheet() {
    openSheet('<h2>بیشتر</h2><div style="display:grid;gap:10px">' +
      '<button class="btn light block" data-go="goals">🎯 اهداف من</button>' +
      '<button class="btn light block" data-go="achievements">🏆 دستاوردها و گزارش</button>' +
      '<button class="btn light block" data-go="assets">💼 وضعیت مالی</button>' +
      '<button class="btn danger block" data-action="reset">↺ بازنشانی داده‌های نمونه</button></div>');
  }

  /* ---------- celebration ---------- */
  function celebrate(o) {
    const el = document.createElement('div');
    el.className = 'celebrate';
    el.innerHTML = '<canvas></canvas><div class="glass-dark"><span class="trophy">' + esc(o.emoji || '🎉') + '</span><h2>' + esc(o.title) + '</h2><p>' + esc(o.text) + '</p>' +
      (o.xp ? '<div class="xp">+' + faN(o.xp) + ' XP</div>' : '') +
      (o.badges && o.badges.length ? '<div class="new-badges">' + o.badges.map((b) => '<span>' + E.BADGES[b].icon + ' ' + E.BADGES[b].title + '</span>').join('') + '</div>' : '') +
      (o.warnings && o.warnings.length ? '<p style="color:#ffc2b8;font-size:12.5px;margin-bottom:12px">⚠️ ' + esc(o.warnings[0]) + '</p>' : '') +
      '<button class="btn primary block">ادامه</button></div>';
    document.getElementById('phone').appendChild(el);
    requestAnimationFrame(() => el.classList.add('open'));
    const stop = confetti(el.querySelector('canvas'));
    const close = () => { stop(); el.classList.remove('open'); setTimeout(() => el.remove(), 300); };
    el.querySelector('button').addEventListener('click', close);
  }

  function confetti(canvas) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr; ctx.scale(dpr, dpr);
    const colors = ['#2fd9a6', '#1d77ac', '#f59342', '#ff7a66', '#f2b33d', '#ffffff'];
    const parts = Array.from({ length: 140 }, () => ({
      x: W / 2 + (Math.random() - 0.5) * 60, y: H * 0.42,
      vx: (Math.random() - 0.5) * 11, vy: -Math.random() * 13 - 4,
      s: Math.random() * 7 + 4, r: Math.random() * 6, vr: (Math.random() - 0.5) * 0.3,
      c: colors[(Math.random() * colors.length) | 0],
    }));
    let raf, t0 = performance.now();
    const tick = (t) => {
      ctx.clearRect(0, 0, W, H);
      parts.forEach((p) => {
        p.vy += 0.32; p.vx *= 0.99; p.x += p.vx; p.y += p.vy; p.r += p.vr;
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c;
        ctx.globalAlpha = Math.max(0, 1 - (t - t0) / 3200);
        ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore();
      });
      if (t - t0 < 3200) raf = requestAnimationFrame(tick);
    };
    if (!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }

  let toastTimer;
  function toast(msg) {
    const el = document.getElementById('toast');
    el.textContent = msg; el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2800);
  }

  function liveMoney(input) {
    const n = parseMoney(input.value);
    input.value = n ? fa(n) : '';
  }

  /* ================================================================== */
  /* What-if (updates in place, no full re-render)                      */
  /* ================================================================== */

  function resetWhatIf() { ui.whatIf = { extra: 0, income: 0, lump: false, invest: false }; }

  function updateWhatIf() {
    const box = document.getElementById('wi-result');
    if (!box) return;
    const goal = state.goals.find((g) => g.id === ui.goalId);
    const w = ui.whatIf;
    const a = E.analyzeProfile(state.profile, state.goals);
    const prof = Object.assign({}, state.profile, { monthlyIncome: state.profile.monthlyIncome * (1 + w.income / 100) });
    const lump = (w.lump ? a.freeCash : 0) + (w.invest ? a.investUsable * 0.25 : 0);
    const base = E.whatIf(state.profile, state.goals, goal.id, now(), {});
    const res = E.whatIf(prof, state.goals, goal.id, now(), { extraMonthly: w.extra, lumpSum: lump });
    document.getElementById('wi-extra-l').textContent = toman(w.extra);
    document.getElementById('wi-income-l').textContent = (w.income > 0 ? '+' : '') + faN(w.income) + '٪';
    const d = isFinite(base.before) && isFinite(res.after) ? base.before - res.after : null;
    let head;
    if (!isFinite(res.after)) head = '<b style="color:var(--coral-2)">دست‌نیافتنی</b>';
    else if (d == null) head = '<b>' + duration(res.after) + '</b>';
    else if (d > 0) head = '<b>' + duration(d) + ' زودتر 🚀</b>';
    else if (d < 0) head = '<b style="color:var(--coral-2)">' + duration(-d) + ' دیرتر</b>';
    else head = '<b style="color:var(--navy-700)">بدون تغییر</b>';
    box.innerHTML = head + '<p>به‌جای ' + (isFinite(base.before) ? jDate(E.addMonths(now(), base.before)) : 'نامشخص') + ' در <b>' + jDate(res.date) + '</b> به «' + esc(goal.name) + '» می‌رسی' +
      (w.invest ? '<br><span style="color:var(--coral-2)">⚠️ فروش سرمایه‌گذاری ریسک دارد و ممکن است در زمان فروش ارزش کمتری داشته باشد.</span>' : '') + '</p>';
  }

  /* ================================================================== */
  /* Router + rendering                                                 */
  /* ================================================================== */

  const VIEWS = { home: viewHome, goals: viewGoals, goal: viewGoal, achievements: viewAchievements, assets: viewAssets };

  function render() {
    const phone = document.getElementById('phone');
    phone.className = 'phone view-' + ui.view;
    document.getElementById('view').innerHTML = VIEWS[ui.view]();
    document.querySelectorAll('.nav-btn').forEach((b) => {
      const v = b.dataset.nav;
      b.classList.toggle('active', v === ui.view || (v === 'home' && (ui.view === 'goals' || ui.view === 'goal')) || (v === 'achievements' && ui.view === 'achievements'));
    });
    // FAB only on goals dashboard
    const fab = document.getElementById('fab');
    if (fab) fab.remove();
    if (ui.view === 'goals') {
      const b = document.createElement('button');
      b.id = 'fab'; b.className = 'fab'; b.dataset.action = 'new-goal'; b.setAttribute('aria-label', 'هدف جدید'); b.innerHTML = I.plus;
      phone.appendChild(b);
    }
    // animate rings
    requestAnimationFrame(() => requestAnimationFrame(() => {
      document.querySelectorAll('.ring-anim').forEach((c) => { c.style.strokeDashoffset = c.dataset.off; });
      layoutRoadmap();
    }));
    if (ui.view === 'goal') updateWhatIf();
  }

  function layoutRoadmap() {
    const rm = document.getElementById('roadmap');
    if (!rm) return;
    const goal = state.goals.find((g) => g.id === ui.goalId);
    const nodes = Array.from(rm.querySelectorAll('.ms'));
    const center = (el) => el.offsetTop + el.querySelector('.node').offsetTop + 25;
    const top = center(nodes[0]);
    let h = 0;
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      if (n.classList.contains('done')) { h = center(n) - top; continue; }
      if (n.classList.contains('current') && i > 0) {
        const prevAmt = +nodes[i - 1].dataset.amount, amt = +n.dataset.amount;
        const f = Math.max(0, Math.min(1, (goal.saved - prevAmt) / (amt - prevAmt || 1)));
        h = (center(nodes[i - 1]) - top) + f * (center(n) - center(nodes[i - 1]));
      }
      break;
    }
    rm.querySelector('#rm-fill').style.top = top + 'px';
    rm.querySelector('#rm-fill').style.height = h + 'px';
  }

  function go(view, goalId) {
    if (view === 'more') { moreSheet(); return; }
    closeSheet();
    document.querySelectorAll('.celebrate').forEach((el) => el.remove());
    ui.view = view;
    if (goalId) { ui.goalId = goalId; resetWhatIf(); }
    render();
    document.getElementById('scroll').scrollTop = 0;
  }

  /* ================================================================== */
  /* Actions                                                            */
  /* ================================================================== */

  function moveGoal(id, dir) {
    const before = plan();
    const ranked = before.ranked.slice();
    const i = ranked.findIndex((g) => g.id === id), j = i + dir;
    if (i < 0 || j < 0 || j >= ranked.length) return;
    const tmp = ranked[i]; ranked[i] = ranked[j]; ranked[j] = tmp;
    ranked.forEach((g, k) => { g.rank = k; });
    recordReplan(before, [{ key: 'priority' }]);
    save(); render();
    toast(j === 0 ? '⭐ «' + ranked[0].name + '» مهم‌ترین هدفت شد' : 'اولویت‌ها به‌روز شد');
  }

  function rebaseline(goal) {
    const p = plan().plans[goal.id];
    goal.baseline = { date: now().toISOString(), saved: goal.saved, monthly: p.scenarios[p.selected].monthly };
    E.logHistory(state.game, now(), 'replan', { goalId: goal.id });
    E.grantBadges(state.game, ['planner'], now());
  }

  const SIMS = {
    raise: (p) => { p.monthlyIncome = Math.round(p.monthlyIncome * 1.15); },
    cost: (p) => { p.fixedExpenses += 400000; },
    gain: (p) => { p.investments.forEach((i) => { i.value = Math.round(i.value * 1.1); }); },
    loss: (p) => { p.investments.forEach((i) => { i.value = Math.round(i.value * 0.85); }); },
  };

  function readProfileForm(form) {
    const p = JSON.parse(JSON.stringify(state.profile));
    form.querySelectorAll('[data-pf]').forEach((el) => {
      const k = el.dataset.pf;
      if (k === 'emergencyMonths') p[k] = Math.max(0, +el.value || 0);
      else if (k === 'savingsReturn') p[k] = Math.max(0, (+el.value || 0) / 100);
      else p[k] = parseMoney(el.value);
    });
    p.investments = Array.from(form.querySelectorAll('[data-inv]')).map((row) => ({
      id: row.dataset.inv, name: row.querySelector('[data-k=name]').value || 'دارایی',
      type: row.querySelector('[data-k=type]').value, value: parseMoney(row.querySelector('[data-k=value]').value),
    }));
    p.debts = Array.from(form.querySelectorAll('[data-debt]')).map((row) => ({
      id: row.dataset.debt, name: row.querySelector('[data-k=name]').value || 'قسط',
      monthlyPayment: parseMoney(row.querySelector('[data-k=monthlyPayment]').value),
      balance: parseMoney(row.querySelector('[data-k=balance]').value),
    }));
    return p;
  }

  function saveProfile(newP) {
    const before = plan();
    const reasons = E.profileChangeReasons(state.profile, newP);
    // a profile edit should keep the previous month's comparison values
    state.profile = newP;
    const n = reasons.length ? recordReplan(before, reasons) : 0;
    save(); render();
    toast(n ? '🗺️ رودمپ ' + faN(n) + ' هدف دوباره محاسبه شد — دلیلش را در صفحه‌ی هر هدف ببین' : 'ذخیره شد');
  }

  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-go],[data-nav],[data-open],[data-action],[data-toast]');
    if (!t) return;
    if (t.dataset.toast) { toast(t.dataset.toast); return; }
    if (t.dataset.nav) { go(t.dataset.nav); return; }
    if (t.dataset.go) { go(t.dataset.go); return; }
    if (t.dataset.open) { go('goal', t.dataset.open); return; }
    const id = t.dataset.id;
    const goal = id && state.goals.find((g) => g.id === id);
    switch (t.dataset.action) {
      case 'toggle-hide': ui.hidden = !ui.hidden; render(); break;
      case 'new-goal': goalForm(null); break;
      case 'edit-goal': goalForm(goal); break;
      case 'deposit': depositSheet(id, +t.dataset.amount || 0); break;
      case 'close-sheet': closeSheet(); break;
      case 'move': moveGoal(id, +t.dataset.dir); break;
      case 'make-top': {
        const before = plan();
        goal.rank = -1; normalizeRanks();
        recordReplan(before, [{ key: 'priority' }]);
        save(); render(); toast('⭐ مهم‌ترین هدفت شد'); break;
      }
      case 'scenario': {
        if (goal.scenario === t.dataset.key) break;
        goal.scenario = t.dataset.key;
        rebaseline(goal);
        save(); render(); toast('سناریوی «' + E.SCENARIOS[goal.scenario].label + '» انتخاب شد و رودمپ به‌روز شد'); break;
      }
      case 'rebaseline': rebaseline(goal); save(); render(); toast('برنامه از امروز به‌روز شد. شروع دوباره، بدون جریمه 💪'); break;
      case 'extend': {
        if (!confirm('مهلت این هدف ' + durationT(+t.dataset.months) + ' تمدید شود؟')) break;
        const before = plan();
        goal.deadline = E.addMonths(goal.deadline, +t.dataset.months).toISOString();
        recordReplan(before, [{ key: 'deadline' }], goal.id);
        rebaseline(goal);
        save(); render(); toast('مهلت تمدید شد'); break;
      }
      case 'complete-goal': {
        if (!confirm('«' + goal.name + '» را خریدی؟ هدف به دستاوردها منتقل می‌شود.')) break;
        goal.status = 'completed'; goal.completedAt = now().toISOString();
        const xp = (goal.reachedMilestones || []).indexOf(100) === -1 ? 500 : 0;
        state.game.xp += xp;
        E.logHistory(state.game, now(), 'complete', { goalId: goal.id });
        const badges = E.grantBadges(state.game, ['goal_done'], now());
        normalizeRanks(); save(); go('goals');
        celebrate({ title: 'مبارکه! 🏆', text: '«' + goal.name + '» به دستاوردهایت اضافه شد.', xp, badges, emoji: '🏆' });
        break;
      }
      case 'delete-goal': {
        if (!confirm('هدف «' + goal.name + '» حذف شود؟ پول کنار گذاشته‌شده در موجودی نقدت باقی می‌ماند.')) break;
        state.goals = state.goals.filter((g) => g.id !== id);
        normalizeRanks(); save(); go('goals'); toast('هدف حذف شد'); break;
      }
      case 'cadence': ui.cadence = t.dataset.key; render(); break;
      case 'whatif-reset': resetWhatIf(); render(); break;
      case 'sim': {
        const form = document.getElementById('profile-form');
        const p = readProfileForm(form);
        SIMS[t.dataset.key](p);
        saveProfile(p); break;
      }
      case 'add-inv': {
        const list = document.getElementById('inv-list');
        const typeOpts = Object.keys(E.ASSET_RULES).map((k) => '<option value="' + k + '">' + E.ASSET_RULES[k].label + '</option>').join('');
        list.insertAdjacentHTML('beforeend', '<div class="inv-row" data-inv="i' + Date.now() + '"><input class="input" data-k="name" placeholder="نام"><select class="input" data-k="type">' + typeOpts + '</select><input class="input money" inputmode="numeric" data-k="value" placeholder="ارزش"><button type="button" data-action="rm-row">×</button></div>');
        break;
      }
      case 'add-debt': {
        document.getElementById('debt-list').insertAdjacentHTML('beforeend', '<div class="inv-row" data-debt="d' + Date.now() + '"><input class="input" data-k="name" placeholder="عنوان"><input class="input money" inputmode="numeric" data-k="monthlyPayment" placeholder="قسط ماهانه"><input class="input money" inputmode="numeric" data-k="balance" placeholder="مانده"><button type="button" data-action="rm-row">×</button></div>');
        break;
      }
      case 'rm-row': t.closest('.inv-row').remove(); break;
      case 'reset':
        if (!confirm('همه‌ی داده‌ها به حالت نمونه برگردد؟')) break;
        state = window.FinSeed.createSeed(new Date()); save(); go('home'); toast('داده‌های نمونه بازنشانی شد'); break;
    }
  });

  document.addEventListener('input', (e) => {
    const el = e.target;
    if (el.dataset && el.dataset.wi) {
      const k = el.dataset.wi;
      ui.whatIf[k] = el.type === 'checkbox' ? el.checked : +el.value;
      updateWhatIf();
      return;
    }
    if (el.closest && el.closest('#profile-form') && el.classList.contains('money')) liveMoney(el);
  });
  document.addEventListener('change', (e) => {
    if (e.target.dataset && e.target.dataset.wi && e.target.type === 'checkbox') { ui.whatIf[e.target.dataset.wi] = e.target.checked; updateWhatIf(); }
  });
  document.addEventListener('submit', (e) => {
    if (e.target.id !== 'profile-form') return;
    e.preventDefault();
    saveProfile(readProfileForm(e.target));
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });

  // Let a URL hash open a view directly (handy for demos): #goals, #goal=g1, #assets, #achievements
  function fromHash() {
    const h = location.hash.slice(1);
    if (!h) return;
    const [v, id] = h.split('=');
    if (v === 'goal' && id) { ui.view = 'goal'; ui.goalId = id; }
    else if (VIEWS[v]) ui.view = v;
  }
  fromHash();
  window.addEventListener('hashchange', () => { fromHash(); closeSheet(); document.querySelectorAll('.celebrate').forEach((el) => el.remove()); render(); });

  save();
  render();
})();
