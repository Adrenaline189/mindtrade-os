let chart;
let currentSymbol = '';
let eventsPage = 1;
const eventsPageSize = 20;
let eventsData = [];

const configuredSymbols = window.DASHBOARD_CONFIG?.symbols || [];

function tabBtn(label, val) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = `symbol-tab-btn ${currentSymbol === val ? 'active' : ''}`;
  b.textContent = label;
  b.addEventListener('click', () => {
    currentSymbol = val;
    renderTabs();
    refreshSummary();
    applyFilters();
  });
  return b;
}

function renderTabs() {
  const wrap = document.getElementById('symbolTabs');
  if (!wrap) return;
  wrap.innerHTML = '';
  wrap.appendChild(tabBtn('ALL', ''));
  configuredSymbols.forEach((s) => wrap.appendChild(tabBtn(s, s)));
}

async function refreshSummary() {
  const qs = currentSymbol ? `?symbol=${encodeURIComponent(currentSymbol)}` : '';
  const res = await fetch(`/api/summary${qs}`);
  const data = await res.json();
  const s = data.summary;

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  setText('k_symbol', currentSymbol || 'ALL');
  setText('k_entries', s.entries);
  setText('k_win', `${s.win_rate}%`);
  setText('k_totalr', s.total_r);
  setText('k_tp', s.tp_hits);
  setText('k_sl', s.sl_hits);
  setText('k_exposure', data.exposure_abs_upnl ?? 0);
  setText('k_positions', data.open_positions_count ?? 0);

  try {
    const fb = await fetch('/api/futures-balance').then((r) => r.json());
    setText('k_futbal', Number(fb.total || 0).toFixed(2));
  } catch (e) {}

  const blockedBox = document.getElementById('blockedBox');
  if (blockedBox) blockedBox.textContent = JSON.stringify(data.blocked_reasons || {}, null, 2);

  const posBody = document.querySelector('#posTable tbody');
  if (posBody) {
    posBody.innerHTML = '';
    (data.open_positions || []).forEach((p) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${p.symbol || ''}</td><td>${p.side || ''}</td><td>${p.contracts || ''}</td><td>${p.entryPrice || ''}</td><td>${p.markPrice || ''}</td><td>${p.unrealizedPnl || ''}</td>`;
      posBody.appendChild(tr);
    });
  }

  const p = await fetch('/api/performance').then((r) => r.json());
  setText('k_maxdd', p.max_dd_r);

  const c = await fetch('/api/connection').then((r) => r.json());
  setText('k_conn', c.ok ? 'OK' : 'ERR');

  setText('ov_entries', s.entries);
  setText('ov_win', `${s.win_rate}%`);
  setText('ov_total_r', s.total_r);
  setText('ov_openpos', data.open_positions_count ?? 0);
  setText('ov_exposure', data.exposure_abs_upnl ?? 0);
  setText('ov_mode', data.mode || 'LIVE');
  setText('ov_conn', c.ok ? 'OK' : 'ERR');
  setText('ov_maxdd', p.max_dd_r);
}

function applyLanguage(lang) {
  const th = {
    txt_title: '📈 MindTrade OS · ธีมโปร', txt_symbols: 'เหรียญ', txt_mode: 'โหมด', txt_maxdd: 'ดรอดาวน์สูงสุด (R)', txt_entries: 'จำนวนเข้าไม้', txt_win: 'อัตราชนะ', txt_totalr: 'รวม R', txt_tp: 'จำนวน TP', txt_sl: 'จำนวน SL',
    txt_conn: 'การเชื่อมต่อ', txt_exposure: 'ความเสี่ยง |uPnL|', txt_openpos: 'โพสิชันที่เปิด', txt_futbal: 'ยอดฟิวเจอร์ (USDT)', txt_events: '🧾 เหตุการณ์ล่าสุด', txt_runtime: '⚙ ตั้งค่าระบบ', txt_blocked: '🚧 เหตุผลที่บล็อก', txt_positions_tbl: '📦 โพสิชันที่เปิด',
    txt_save_btn: 'บันทึก', txt_start_btn: '▶ เริ่ม', txt_stop_btn: '⏹ หยุด', txt_panic_btn: '🛑 หยุดฉุกเฉิน', txt_unpanic_btn: '✅ ปลดฉุกเฉิน'
  };
  const en = {
    txt_title: '📈 MindTrade OS · Pro Theme', txt_symbols: 'Symbols', txt_mode: 'Mode', txt_maxdd: 'Max DD (R)', txt_entries: 'Entries', txt_win: 'Win Rate', txt_totalr: 'Total R', txt_tp: 'TP Hits', txt_sl: 'SL Hits',
    txt_conn: 'Connection', txt_exposure: 'Exposure |uPnL|', txt_openpos: 'Open Positions', txt_futbal: 'Futures Balance (USDT)', txt_events: '🧾 Latest Events', txt_runtime: '⚙ Runtime Settings', txt_blocked: '🚧 Blocked Reasons', txt_positions_tbl: '📦 Open Positions',
    txt_save_btn: 'Save', txt_start_btn: '▶ START', txt_stop_btn: '⏹ STOP', txt_panic_btn: '🛑 PANIC', txt_unpanic_btn: '✅ UNPANIC'
  };
  const dict = lang === 'th' ? th : en;
  Object.keys(dict).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = dict[id];
  });
  localStorage.setItem('dash_lang', lang);
}

function toBangkokTime(v) {
  try {
    if (!v) return '';
    const raw = String(v).trim();

    // Trade logs are stored in UTC without timezone suffix, e.g. "2026-03-03 15:00:00"
    // Normalize to ISO-UTC before parsing so browser local timezone won't skew output.
    let iso = raw;
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(raw)) {
      iso = raw.replace(' ', 'T') + 'Z';
    } else if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(raw)) {
      iso = raw + 'Z';
    }

    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return raw;
    return d.toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', hour12: false });
  } catch (e) {
    return String(v || '');
  }
}

function renderEventsPage() {
  const filterSymbol = document.getElementById('filterSymbol');
  const filterResult = document.getElementById('filterResult');
  if (!filterSymbol || !filterResult) return;

  if (currentSymbol) filterSymbol.value = currentSymbol;
  const fs = filterSymbol.value;
  const fr = filterResult.value;
  const filtered = eventsData.filter((e) => (!fs || (e.symbol || '-') === fs) && (!fr || (e.result || '') === fr));

  const totalPages = Math.max(1, Math.ceil(filtered.length / eventsPageSize));
  if (eventsPage > totalPages) eventsPage = totalPages;
  const start = (eventsPage - 1) * eventsPageSize;
  const pageItems = filtered.slice(start, start + eventsPageSize);

  const tb = document.querySelector('#eventsTable tbody');
  if (tb) {
    tb.innerHTML = '';
    pageItems.forEach((t) => {
      const tr = document.createElement('tr');
      tr.dataset.symbol = t.symbol || '-';
      tr.dataset.result = t.result || '';
      tr.innerHTML = `<td>${toBangkokTime(t.time) || ''}</td><td>${t.symbol || '-'}</td><td>${t.bias || ''}</td><td>${t.rsi || ''}</td><td><span class="tag ${t.result || ''}">${t.result || ''}</span></td><td>${t.note || ''}</td>`;
      tb.appendChild(tr);
    });
  }

  const info = document.getElementById('evtPageInfo');
  if (info) info.textContent = `Page ${eventsPage}/${totalPages}`;
  const prev = document.getElementById('evtPrev');
  const next = document.getElementById('evtNext');
  if (prev) prev.disabled = eventsPage <= 1;
  if (next) next.disabled = eventsPage >= totalPages;
}

async function loadEventsData() {
  try {
    const res = await fetch('/api/events?limit=500');
    const data = await res.json();
    eventsData = (data.events || []).slice().reverse();

    const syms = [...new Set(eventsData.map((e) => e.symbol).filter(Boolean))].sort();
    const sel = document.getElementById('filterSymbol');
    if (sel) {
      sel.innerHTML = '<option value="">All Symbols</option>';
      syms.forEach((v) => {
        const o = document.createElement('option');
        o.value = v;
        o.textContent = v;
        sel.appendChild(o);
      });
    }
    eventsPage = 1;
    renderEventsPage();
  } catch (e) {}
}

function applyFilters(resetPage = false) {
  if (resetPage) eventsPage = 1;
  renderEventsPage();
}

async function refreshLeverage() {
  try {
    const data = await fetch('/api/leverage').then((r) => r.json());
    const tb = document.querySelector('#levTable tbody');
    if (!tb) return;
    tb.innerHTML = '';
    (data.rows || []).forEach((x) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${x.symbol}</td><td>${x.leverage}x</td><td>${x.margin_mode}</td>`;
      tb.appendChild(tr);
    });
  } catch (e) {}
}

function initHelpWidget() {
  const helpBtn = document.getElementById('helpWidgetToggle');
  const helpBox = document.getElementById('helpWidget');
  const helpClose = document.getElementById('helpWidgetClose');
  const helpSend = document.getElementById('helpWidgetSend');
  const helpQ = document.getElementById('helpWidgetQ');
  const helpLog = document.getElementById('helpWidgetLog');

  const helpOpen = () => {
    if (!helpBox) return;
    helpBox.classList.add('open');
    if (helpBtn) helpBtn.classList.add('hidden');
  };

  const helpHide = () => {
    if (!helpBox) return;
    helpBox.classList.remove('open');
    if (helpBtn) helpBtn.classList.remove('hidden');
  };

  const helpAsk = async () => {
    if (!helpQ || !helpLog) return;
    const q = (helpQ.value || '').trim();
    if (!q) return;
    helpLog.textContent += `\n\nคุณ: ${q}`;
    helpQ.value = '';
    try {
      const res = await fetch('/api/help-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      });
      const data = await res.json();
      helpLog.textContent += `\nน้องมายด์: ${data.answer || '-'}`;
    } catch (e) {
      helpLog.textContent += '\nน้องมายด์: ระบบช่วยเหลือมีปัญหาชั่วคราวค่ะ';
    }
    helpLog.scrollTop = helpLog.scrollHeight;
  };

  if (helpBtn) helpBtn.addEventListener('click', helpOpen);
  if (helpClose) helpClose.addEventListener('click', helpHide);
  if (helpSend) helpSend.addEventListener('click', helpAsk);
  if (helpQ) {
    helpQ.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') helpAsk();
    });
  }
}

function initApiTest() {
  const btnTestApi = document.getElementById('btnTestApi');
  const apiTestResult = document.getElementById('apiTestResult');
  if (!btnTestApi || !apiTestResult) return;

  btnTestApi.addEventListener('click', async () => {
    apiTestResult.textContent = 'testing...';
    try {
      const r = await fetch('/settings/api/test', { method: 'POST' });
      const d = await r.json();
      apiTestResult.textContent = d.ok ? `OK • USDT ${Number(d.usdt_total || 0).toFixed(2)}` : `ERR • ${d.error || 'unknown'}`;
    } catch (e) {
      apiTestResult.textContent = 'ERR • request failed';
    }
  });
}

function initLangSwitcher() {
  const langSel = document.getElementById('langSwitch');
  if (!langSel) return;
  const saved = localStorage.getItem('dash_lang') || 'th';
  langSel.value = saved;
  applyLanguage(saved);
  langSel.addEventListener('change', (e) => applyLanguage(e.target.value));
}

function initStaticEvents() {
  const filterSymbolEl = document.getElementById('filterSymbol');
  const filterResultEl = document.getElementById('filterResult');
  const evtPrev = document.getElementById('evtPrev');
  const evtNext = document.getElementById('evtNext');

  if (filterSymbolEl) filterSymbolEl.addEventListener('change', () => applyFilters(true));
  if (filterResultEl) filterResultEl.addEventListener('change', () => applyFilters(true));
  if (evtPrev) evtPrev.addEventListener('click', () => {
    eventsPage = Math.max(1, eventsPage - 1);
    renderEventsPage();
  });
  if (evtNext) evtNext.addEventListener('click', () => {
    eventsPage += 1;
    renderEventsPage();
  });
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/service-worker.js').catch(() => {});
  });
}

renderTabs();
loadEventsData();
refreshSummary();
refreshLeverage();
initLangSwitcher();
initHelpWidget();
initApiTest();
initStaticEvents();

setInterval(() => {
  refreshSummary();
  refreshLeverage();
}, 10000);
