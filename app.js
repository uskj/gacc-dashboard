const API_BASE = location.protocol.startsWith('http') ? location.origin + '/data' : './data';
const STATES = { "核心":"core","重点":"focus","准入":"ok","部分":"part","暂停":"pause","未准入":"none","未跟踪":"na" };
const CORE_ONLY = ["核心","重点"];

let DATA = null;
let showAll = false;
let autoTimer = null;

async function load() {
  try {
    const r = await fetch(API_BASE + '/latest.json?t=' + Date.now(), { cache: 'no-store' });
    DATA = await r.json();
  } catch {
    const r = await fetch(API_BASE + '/countries.json?t=' + Date.now(), { cache: 'no-store' });
    DATA = await r.json();
  }
  document.getElementById('dataDate').textContent = DATA.dataDate || (DATA._meta && DATA._meta.dataDate) || '--';
  document.getElementById('lastUpd').textContent = DATA.generated_at ? DATA.generated_at.split(' ')[1] : new Date().toLocaleTimeString('zh-CN');
  renderSup();
  renderSubDrill();
  renderSources();
  renderNews();
  renderCifer();
  renderAlerts();
}

async function renderAlerts() {
  const card = document.getElementById('alertCard');
  const box = document.getElementById('alertBody');
  if (!card || !box) return;
  let a = null;
  try {
    const r = await fetch(API_BASE + '/alerts.json?t=' + Date.now(), { cache: 'no-store' });
    a = await r.json();
  } catch { card.style.display = 'none'; return; }
  const list = (a && a.alerts) || [];
  document.getElementById('alertDate').textContent = (a && a.generated ? a.generated.slice(11, 16) : '--');
  document.getElementById('alertN').textContent = list.length;
  if (!list.length) { card.style.display = 'none'; return; }
  card.style.display = '';
  box.innerHTML = list.map(x => {
    const cls = x.kind === 'ban' ? 'ban' : (x.kind === 'lift' ? 'lift' : 'access');
    const top = (x.top || []).length ? `<div class="l2">相关企业：${x.top.map(esc).join(' ｜ ')}</div>` : '';
    return `<div class="alrt">
      <div class="l1">
        <span class="badge ${cls}">${esc(x.kindLabel)}</span>
        <b>${esc(x.source)} ${esc(x.number || '')}</b>
        <span class="dim">${esc(x.date || '')}</span>
        <span class="dim">· 命中 <b>${x.matched}</b> 家${x.suspended ? `（暂停等 ${x.suspended}）` : ''}</span>
        <span class="dim" style="margin-left:auto">${esc(x.countryLabel || (x.countries || []).join('、'))}</span>
      </div>
      <div class="l2"><a href="${esc(x.url || '#')}" target="_blank" rel="noopener">${esc(x.title)}</a></div>
      ${top}
    </div>`;
  }).join('');
}

function esc(s){ s = String(s==null?'':s); return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function renderSources() {
  const notes = DATA.source_notes || {};
  const feeds = DATA.feeds || {};
  const gacc = DATA.gacc_sources || [];
  const rows = Object.keys(feeds).map(k => {
    const f = feeds[k];
    const ok = f && f.status === 'ok';
    const items = (f && f.items ? f.items.length : 0);
    const err = f && f.error ? (f.error || '').slice(0, 70) : '';
    return `<div class="newsit">
      <div class="nhead">
        <span class="badge ${ok?'ok':'bad'}">${ok?'● 自动抓取':'⚠ ' + esc(f.status||'blocked')}</span>
        <b>${esc(k)}</b> <span class="dim">· ${esc((notes[k]||'').split('·')[0])}</span>
        <span class="dim" style="float:right">${items} 条</span>
      </div>
      ${err?`<div class="dim" style="margin-top:4px">${esc(err)}</div>`:''}
      ${notes[k]?`<div class="dim" style="margin-top:2px">${esc(notes[k])}</div>`:''}
    </div>`;
  }).join('');
  const gaccRows = gacc.map(c => `<div class="newsit">
    <div class="nhead"><span class="badge bad">⚠ 人工核验</span><b>${esc(c.label)}</b></div>
    <div class="dim" style="margin-top:2px">${esc(c.note)}</div>
    <div style="margin-top:4px"><a href="${esc(c.url)}" target="_blank" rel="noopener">到 GACC 官网核验 ↗</a></div>
  </div>`).join('');
  const el = document.getElementById('srcBody');
  if (el) el.innerHTML = `<div class="srcgrp"><div class="sg"><b>自动抓取源（${Object.keys(feeds).length} 个）</b></div>${rows}</div>
    <div class="srcgrp" style="margin-top:14px"><div class="sg"><b>GACC 权威核验入口（Cloudflare 拦截自动抓取 → 人工核验）</b></div>${gaccRows}</div>` +
    `<div class="dim" style="margin-top:12px;font-size:12px">数据口径：矩阵格值以 GACC 公开名单 + 280 号令为准；自动更新仅覆盖可直连官方源。MAPA / SENASA 被反爬时明确标 blocked，不伪造。</div>`;
}

function renderNews() {
  const news = DATA.news || [];
  if (!news.length) { const el = document.getElementById('newsBody'); if (el) el.innerHTML = '<div class="dim">暂无可展示新闻</div>'; return; }
  const bySrc = {};
  news.forEach(n => { (bySrc[n.src] = bySrc[n.src] || []).push(n); });
  const el = document.getElementById('newsBody');
  if (el) el.innerHTML = Object.keys(bySrc).map(src => {
    const items = bySrc[src].slice(0, 5).map(n => `<div class="newsit">
      <a href="${esc(n.url||'#')}" target="_blank" rel="noopener"><b>${esc(n.title||'')}</b></a>
      <div class="dim">${esc(n.country||'')} · ${esc(n.src||'')} · ${esc(n.date||'')}</div>
    </div>`).join('');
    return `<div class="srcgrp"><div class="sg"><b>${esc(src)}</b> · ${bySrc[src].length} 条</div>${items}</div>`;
  }).join('');
}

function countries() {
  return DATA.countries || [];
}

function cellCls(v) { return v && STATES[v] ? STATES[v] : 'na'; }
function cellText(v) { return v || ''; }

function renderSup() {
  const catsG = DATA.categories;
  const ciferCountries = (DATA.cifer && DATA.cifer.countries) || [];
  const head = document.getElementById('supHead');
  const body = document.getElementById('supBody');
  if (!head || !body) return;

  // GACC 21 类里, 哪些被 "核心/重点" 占用 (该格是国别优先级, 不是准入状态)
  const prioCat = '肉与肉制品';

  head.innerHTML = `<tr>
      <th class="c0" title="GACC 转录重点国别">国别</th>
      <th title="GACC 国别优先级分级">优先级</th>
      <th title="GACC 转录 21 类制度准入状态">GACC 准入状态</th>
      <th title="CIFER 在册注册工厂总数">CIFER 注册工厂</th>
      <th title="CIFER 注册数最高的 3 个品类">CIFER Top3 品类</th>
      <th title="UN Comtrade 中国自该国进口额(CIF, 美元)。2025 为主值，含 2024 对比；2026 年 Comtrade 未发布">对华进口额</th>
      <th title="该国主管当局">主管当局</th>
    </tr>`;

  body.innerHTML = countries().map(ct => {
    const cells = ct.cells || {};
    const prio = cells[prioCat] && CORE_ONLY.includes(cells[prioCat]) ? cells[prioCat] : '';
    const prioTxt = prio ? `<span class="c ${cellCls(prio)}" style="display:inline-block">${prio}</span>` : '<span class="c na">—</span>';

    // GACC 制度状态: 排除“核心/重点”(那是分级), 统计准入/部分/暂停/未准入/未跟踪
    const stCnt = {};
    Object.entries(cells).forEach(([cat, v]) => {
      if (cat === prioCat && CORE_ONLY.includes(v)) return; // 分级格不算制度状态
      if (!v) return;
      stCnt[v] = (stCnt[v] || 0) + 1;
    });
    const stTxt = Object.entries(stCnt).length
      ? Object.entries(stCnt).map(([st, n]) => `<span class="c ${cellCls(st)}" style="display:inline-block;margin-right:4px">${st} ${n}类</span>`).join('')
      : '<span class="c na">空白</span>';

    // CIFER 匹配(code2 == GACC code)
    const ce = ciferCountries.find(x => x.code2 === ct.code);
    const sum = ce ? Object.values(ce.cells).reduce((a, b) => a + b, 0) : 0;
    const top3 = ce
      ? Object.entries(ce.cells).sort((a, b) => b[1] - a[1]).slice(0, 3)
          .map(([cat, n]) => `${ciferLab(cat)} ${n}家`).join(' · ')
      : '<span class="c na">无注册</span>';
    const ciferCell = ce
      ? `<span class="c ok" style="display:inline-block">${sum} 家</span>`
      : '<span class="c na">—</span>';

    // 第三维度: UN Comtrade 进口额 (2025 主值, 2024 对比)
    const imp = ct.imports || {};
    let impCell;
    if (imp.complete && imp.totalUSD > 0) {
      const m = imp.totalUSD / 1e6;
      const pv = imp.prev || {};
      let yoy = '';
      if (pv.complete && pv.totalUSD > 0) {
        const d = (imp.totalUSD - pv.totalUSD) / pv.totalUSD * 100;
        yoy = `<span class="dim" style="font-size:11px;margin-left:4px">${d >= 0 ? '▲' : '▼'}${Math.abs(d).toFixed(1)}%</span>`;
      }
      const topCats = (imp.top3 || []).map(x => `${x.cat} $${(x.usd/1e6).toFixed(0)}M`).join(' · ');
      impCell = `<span class="c ok imp" style="display:inline-block;color:#16607f" title="${esc(topCats)}">${esc(String(imp.year||''))} $${(m/1e3).toFixed(2)}B</span>${yoy}`;
    } else if (imp.complete === false) {
      impCell = '<span class="c na">待补配额</span>';
    } else {
      impCell = '<span class="c na">—</span>';
    }

    // 2026 镜像 (伙伴国对华出口 FOB, 已报送月份合计)
    const imp26 = ct.imports26 || {};
    let imp26Cell = '';
    if (imp26.complete && imp26.totalUSD > 0) {
      const ms = imp26.months || [];
      const mm = ms.length ? `${ms[0]}${ms.length > 1 ? '–' + ms[ms.length - 1] : ''}月` : '';
      const y26 = imp26.yoy != null
        ? `<span class="dim" style="font-size:11px;margin-left:4px">${imp26.yoy >= 0 ? '▲' : '▼'}${Math.abs(imp26.yoy).toFixed(1)}%</span>` : '';
      imp26Cell = `<div class="dim" style="margin-top:3px" title="镜像口径: 伙伴国报送的对华出口(FOB), 非中国CIF"><span style="font-size:11px">2026 ${mm}镜像</span> <b style="font-size:12px;color:#16607f">$${(imp26.totalUSD/1e6/1000).toFixed(2)}B</b>${y26}</div>`;
    }

    // leadPriority 真需求标注
    const lp = ct.leadPriority;
    const lpBadge = lp && lp.tier && lp.tier !== '—'
      ? `<span class="dim" style="font-size:11px;margin-left:6px;color:#b03030" title="${esc(lp.label)}${lp.reason ? ' — ' + esc(lp.reason) : ''}">[${esc(lp.tier)}]</span>` : '';

    return `<tr class="suprow" data-cd="${esc(ct.code)}">
      <td class="c0"><span class="fl">${ct.flag||''}</span><b>${esc(ct.name)}</b>${lpBadge}<div class="cd">${esc(ct.code)} · ${esc(ct.auth||'')}</div></td>
      <td>${prioTxt}</td>
      <td class="tl">${stTxt}</td>
      <td>${ciferCell}</td>
      <td class="tl"><span class="dim">${top3}</span></td>
      <td class="tl">${impCell}${imp26Cell}</td>
      <td class="tl"><span class="dim">${esc(ct.auth||'—')}</span></td>
    </tr>`;
  }).join('');

  document.querySelectorAll('#supBody tr.suprow').forEach(tr => {
    tr.addEventListener('click', () => showSupDetail(tr.dataset.cd));
  });

  renderVerifiedLeads();
}

function renderVerifiedLeads() {
  const vl = DATA.verifiedLeads2025 || {};
  const card = document.getElementById('vlCard');
  const body = document.getElementById('vlBody');
  if (!card || !body) return;
  const rows = Object.entries(vl).filter(([, v]) => v.complete && v.totalUSD > 0);
  if (!rows.length) { card.style.display = 'none'; return; }
  // 按优先级 tier 排序 (D 盘/真需求重的在前)
  const tierRank = (t) => {
    t = t || '';
    if (t.includes('时效')) return 0;
    if (t === 'A' || t === 'A/B') return 1;
    if (t === 'A3' || t === 'A1') return 2;
    if (t === 'D') return 3;
    if (t === '弱') return 4;
    return 5;
  };
  rows.sort((a, b) => tierRank(a[1].leadPriority && a[1].leadPriority.tier) - tierRank(b[1].leadPriority && b[1].leadPriority.tier));
  card.style.display = '';
  body.innerHTML = rows.map(([code, v]) => {
    const lp = v.leadPriority || {};
    const imp = (DATA.countries.find(c => c.code === code) || {}).imports || {};
    const yoy = (imp.prev && imp.prev.complete && imp.prev.totalUSD > 0)
      ? (() => { const d = (imp.totalUSD - imp.prev.totalUSD) / imp.prev.totalUSD * 100; return `<span class="${d>=0?'ok':'na'}" style="font-size:11px;margin-left:4px">${d>=0?'▲':'▼'}${Math.abs(d).toFixed(1)}%</span>`; })() : '';
    const top3 = (v.top3 || []).map(x => `<span class="k">${esc(x.cat)}</span><span class="ok">$${(x.usd/1e6).toFixed(0)}M</span>`).join('');
    return `<div class="srcgrp" style="margin-bottom:14px">
      <div class="sg"><b>${code}</b> <span class="dim">2025 对华食品进口</span>
        ${lp.tier ? `<span class="c part" style="font-size:10px;margin-left:6px">[${esc(lp.tier)}]</span>` : ''}
      </div>
      <div style="font-size:14px;margin:4px 0"><b>$${(v.totalUSD/1e6).toFixed(0)}M</b> CIF</div>
      ${lp.label ? `<div class="dim" style="font-size:12px">${esc(lp.label)}${lp.reason ? ' — ' + esc(lp.reason) : ''}</div>` : ''}
      <div class="kv" style="margin-top:6px">${top3}</div>
    </div>`;
  }).join('');
}

function showSupDetail(code) {
  const ct = DATA.countries.find(x => x.code === code);
  if (!ct) return;
  const cells = ct.cells || {};
  const ce = ((DATA.cifer||{}).countries||[]).find(x => x.code2 === code);
  const prioCat = '肉与肉制品';
  const prio = cells[prioCat] && CORE_ONLY.includes(cells[prioCat]) ? cells[prioCat] : '';

  // GACC 制度状态明细 (排除分级格)
  const gRows = Object.entries(cells).filter(([cat, v]) => !(cat === prioCat && CORE_ONLY.includes(v)) && v)
    .map(([cat, v]) => `<span class="k">${cat}</span><span class="c ${cellCls(v)}" style="display:inline-block">${v}</span>`).join('')
    || '<span class="k">21 类</span><span class="c na">空白（区段未转录）</span>';

  // CIFER 31 类明细
  const cRows = ce
    ? DATA.cifer.categories.map(k => {
        const v = ce.cells[k] || 0;
        return `<span class="k">${k}</span><span class="${v>0?'ok':'na'}">${v>0? v+' 家': '无注册'}</span>`;
      }).join('')
    : '<span class="k">CIFER</span><span class="c na">无该国家部记录</span>';

  // 第三维度: UN Comtrade 进口额明细 (2025 主值, 2024 对比)
  const imp = ct.imports || {};
  const impPrev = imp.prev || {};
  const imp2 = DATA._meta && DATA._meta.imports3d || {};
  let impRows;
  if (imp.complete && imp.totalUSD > 0) {
    const rows = (imp.top3 || []).map(x =>
      `<span class="k">${esc(x.cat)}</span><span class="ok">$${(x.usd/1e6).toFixed(0)}M</span>`).join('')
      || '<span class="k">分章</span><span class="na">见 breakdown</span>';
    let prevLine = '';
    if (impPrev.complete && impPrev.totalUSD > 0) {
      const d = (imp.totalUSD - impPrev.totalUSD) / impPrev.totalUSD * 100;
      prevLine = `<div style="margin-top:6px;font-size:13px"><span class="dim">${esc(String(impPrev.year||2024))} 全年</span> <b>$${(impPrev.totalUSD/1e6/1000).toFixed(2)}B</b> <span class="${d>=0?'ok':'na'}" style="margin-left:4px">${d>=0?'▲':'▼'}${Math.abs(d).toFixed(1)}%</span></div>`;
    }
    impRows = `<div style="font-size:14px"><span class="c ok imp">${esc(String(imp.year||''))} 全年</span> <b>$${(imp.totalUSD/1e6/1000).toFixed(2)}B</b> CIF</div>
      <div class="kv" style="margin-top:6px">${rows}</div>
      ${prevLine}
      <div class="dim" style="margin-top:4px;font-size:11px">2026 年 UN Comtrade 尚未发布（中国未报送，annual/monthly 均无）；源：${esc(imp.source||'')}</div>`;
  } else if (imp.complete === false) {
    impRows = '<div class="c na">该国家进口额待补：UN Comtrade 免费预览当日配额用尽，次日自动续抓。</div>';
  } else {
    impRows = '<div class="c na">无进口额数据。</div>';
  }
  if (impRows && imp2 && imp2.pending && imp2.pending.length) {
    impRows += `<div class="dim" style="margin-top:4px;font-size:11px">待补国家：${esc(imp2.pending.join(' / '))}</div>`;
  }

  // 2026 镜像口径 (伙伴国对华出口 FOB, 已报送月份合计)
  const imp26 = ct.imports26 || {};
  let imp26Rows = '';
  if (imp26.complete && imp26.totalUSD > 0) {
    const ms = imp26.months || [];
    const mm = ms.length ? `${ms[0]}${ms.length > 1 ? '–' + ms[ms.length - 1] : ''} 月` : '';
    const y26 = imp26.yoy != null
      ? `<span class="${imp26.yoy >= 0 ? 'ok' : 'na'}" style="margin-left:4px">${imp26.yoy >= 0 ? '▲' : '▼'}${Math.abs(imp26.yoy).toFixed(1)}%</span>` : '';
    const r26 = (imp26.top3 || []).map(x =>
      `<span class="k">${esc(x.cat)}</span><span class="ok">$${(x.usd/1e6).toFixed(0)}M</span>`).join('');
    imp26Rows = `<div style="margin-top:10px;font-size:14px"><span class="c part imp">2026 ${mm}·镜像</span> <b>$${(imp26.totalUSD/1e6/1000).toFixed(2)}B</b> FOB${y26}</div>
      <div class="kv" style="margin-top:6px">${r26}</div>
      <div class="dim" style="margin-top:4px;font-size:11px">口径：伙伴国报送的对华出口(FOB)，非中国 CIF；同比为 2025 同月合计。中国尚未向 Comtrade 报送 2026，此为镜像估算。</div>`;
  } else {
    imp26Rows = `<div class="dim" style="margin-top:10px;font-size:12px">2026：中国未向 Comtrade 报送；伙伴国镜像数据暂无（该国未向 Comtrade 报送对华月度出口，或配额待续）。</div>`;
  }

  document.getElementById('popT').textContent = `${ct.flag||''} ${ct.name} · 双源对照`;
  document.getElementById('popB').innerHTML = `
    <div class="srcgrp">
      <div class="sg"><b>GACC 转录 · 制度准入状态</b><span class="dim" style="float:right">${prio?`优先级 <span class="c ${cellCls(prio)}">${prio}</span>`:'无分级'}</span></div>
      <div class="kv">${gRows}</div>
      <div class="dim" style="margin-top:6px">主管当局：${esc(ct.auth||'—')} · <a href="${esc(ct.url||'#')}" target="_blank" rel="noopener">当局官网 ↗</a></div>
    </div>
    <div class="srcgrp" style="margin-top:14px">
      <div class="sg"><b>CIFER 官方库 · 注册工厂覆盖</b><span class="dim" style="float:right">${ce? '合计 '+Object.values(ce.cells).reduce((a,b)=>a+b,0)+' 家' : ''}</span></div>
      <div class="kv">${cRows}</div>
    </div>
    <div class="srcgrp" style="margin-top:14px">
      <div class="sg"><b>UN Comtrade · 对华进口额 (2024/2025 CIF · 2026 镜像)</b></div>
      ${impRows}
      ${imp26Rows}
    </div>
    ${(()=>{ const vl=(DATA.verifiedLeads2025||{})[code]; if(!vl||!vl.complete||!vl.totalUSD) return ''; const lp=vl.leadPriority||{}; const rows=(vl.top3||[]).map(x=>`<span class="k">${esc(x.cat)}</span><span class="ok">$${(x.usd/1e6).toFixed(0)}M</span>`).join(''); return `<div class="srcgrp" style="margin-top:14px"><div class="sg"><b>真需求·进口实据 (${code} 对华食品进口 2025)</b></div><div style="font-size:14px;margin-top:6px"><b>$${(vl.totalUSD/1e6).toFixed(0)}M</b> CIF${lp.tier?` <span class="dim" style="font-size:11px">[${esc(lp.tier)}]</span>`:''}</div>${lp.label?`<div class="dim" style="font-size:12px;margin-top:4px">${esc(lp.label)}${lp.reason?' — '+esc(lp.reason):''}</div>`:''}<div class="kv" style="margin-top:6px">${rows}</div></div>`; })()}
    <div style="margin-top:12px;color:var(--dim);font-size:12px">
      三源口径互异：制度状态（准入/部分/暂停）为政策资格；注册覆盖为企业数；进口额为实际贸易量（美元）。互为补充，不做归约。
    </div>`;
  document.getElementById('mask').classList.add('show');
}

function renderSubDrill() {
  const s = DATA.subDrill || {};
  document.getElementById('subTitle').textContent = (s.title || '子品类下钻').replace('★ ','').replace('★','');
  document.getElementById('subCov').textContent = s.coverage || '--';
  document.getElementById('subDate').textContent = s.dataDate || '--';
  // 物种×部位 子矩阵 (示意: 肉与肉制品)
  const species = ['牛','羊','猪','鸡','鸭','牛(冻)','牛(鲜)','羊(冻)'];
  const parts = ['整块','部位分割','碎肉','内脏','头蹄','皮','骨','油'];
  document.getElementById('subHead').innerHTML =
    '<tr><th>国别\\部位</th>' + parts.map(p => `<th>${p}</th>`).join('') + '</tr>';
  // 仅对已准入肉类的国家填子格 (示例逻辑)
  const meat = DATA.countries.filter(c => c.cells['肉与肉制品']);
  document.getElementById('subBody').innerHTML = meat.map(c => {
    const v = c.cells['肉与肉制品'];
    const st = cellCls(v);
    // 演示: 核心国别整块+部位分割准入, 其他留空; 实际由抓取器填充
    const cells = parts.map((p,i) => {
      if ((v==='核心'||v==='重点') && i<2) return `<td><span class="c ok">准入</span></td>`;
      return '<td><span class="c na">·</span></td>';
    }).join('');
    return `<tr><td class="tl"><b>${c.flag} ${c.name}</b></td>${cells}</tr>`;
  }).join('');
}

function showDetail(code, cat) {
  const c = DATA.countries.find(x => x.code === code);
  if (!c) return;
  const v = c.cells[cat] || '未跟踪';
  const st = cellCls(v);
  document.getElementById('popT').textContent = `${c.flag} ${c.name} · ${cat}`;
  document.getElementById('popB').innerHTML = `
    <div>当前状态：<span class="c ${st}" style="display:inline-block">${v}</span></div>
    <div class="kv">
      <span class="k">主管当局</span><span>${c.auth||'—'}</span>
      <span class="k">当局官网</span><span><a href="${c.url||'#'}" target="_blank" rel="noopener">${(c.url||'').replace(/^https?:\/\//,'')||'—'}</a></span>
      <span class="k">制度依据</span><span>280 号令 · 17 类目录（${(DATA._meta||{}).effective||'2026-06-01'} 施行）</span>
      <span class="k">数据日期</span><span>${DATA.dataDate||'--'}</span>
      <span class="k">核对入口</span><span><a href="${c.url||'#'}" target="_blank" rel="noopener">到当局官网核验 ↗</a> · GACC 侧公告</span>
    </div>
    <div style="margin-top:12px;color:var(--dim);font-size:12px">
      ${DATA._meta&&DATA._meta.note||''}
    </div>`;
  document.getElementById('mask').classList.add('show');
}
document.getElementById('popX').addEventListener('click', () => document.getElementById('mask').classList.remove('show'));
document.getElementById('mask').addEventListener('click', e => { if (e.target.id==='mask') e.target.classList.remove('show'); });

// 人工 18 国矩阵: 默认折叠 (副表), 通过 btnFold 切换
function toggleFold() {
  const fold = document.getElementById('mxFold');
  const btn = document.getElementById('btnFold');
  const hidden = fold.style.display === 'none';
  fold.style.display = hidden ? '' : 'none';
  btn.textContent = hidden ? '折叠' : '展开';
}
document.getElementById('btnFold').addEventListener('click', toggleFold);
toggleFold();

document.getElementById('btnRefresh').addEventListener('click', async () => {
  const b = document.getElementById('btnRefresh');
  if (b.dataset.busy) return;
  b.dataset.busy = '1';
  b.innerHTML = '刷新中…';
  try { await fetch(API_BASE + '/refresh?1=1', { method: 'POST' }).catch(()=>{});
    await new Promise(r => setTimeout(r, 1500)); await load(); b.innerHTML = '✓ 已刷新'; }
  catch { b.innerHTML = '刷新失败'; }
  setTimeout(() => { b.innerHTML = '刷新'; delete b.dataset.busy; }, 1600);
});

/* ===== 左侧导航统一路由: 有内容则滚动定位, 无内容则弹「规划中」 ===== */
function openPlanModal(name) {
  document.getElementById('popT').textContent = `${name} · 规划中`;
  document.getElementById('popB').innerHTML =
    '<div style="font-size:14px">「<b>' + esc(name) + '</b>」属 STGACC 业务系统规划范围。</div>' +
    '<div style="margin-top:10px;color:var(--dim);font-size:12px;line-height:1.7">' +
    '当前 v1.0 仅交付「准入情报」模块：仪表盘 / 政策雷达 / 准入情报矩阵 / 工厂动态 / GACC 注册矩阵 / 境外企业准入名录 / 工厂档案 / 数据源与核对。其余模块规划中，敬请期待。</div>';
  document.getElementById('mask').classList.add('show');
}
document.getElementById('menu').addEventListener('click', e => {
  const mi = e.target.closest('.mi');
  if (!mi) return;
  document.querySelectorAll('#menu .mi').forEach(x => x.classList.remove('on'));
  mi.classList.add('on');
  if (mi.dataset.go === 'top') { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
  const t = mi.dataset.go && document.getElementById(mi.dataset.go);
  if (t) {
    if (mi.dataset.go === 'mxCard') {
      const f = document.getElementById('mxFold');
      if (f && f.style.display === 'none') toggleFold();
    }
    t.scrollIntoView({ behavior: 'smooth', block: 'start' });
    t.style.outline = '2px solid var(--acc)';
    setTimeout(() => { t.style.outline = ''; }, 2000);
    return;
  }
  openPlanModal(mi.dataset.plan || mi.textContent.trim());
});

function startAuto() { clearInterval(autoTimer); autoTimer = setInterval(load, 60000); }

/* ===== GACC CIFER 权威注册矩阵 (183 国 × 31 品类) ===== */
/* CIFER 品类缩写表头 (太长竖排会挡数字, 用短标签 + title 显示全名) */
const CIFER_SHORT = {
  "特殊膳食食品（不包括乳基婴幼儿配方食品）": "特殊膳食",
  "糖果、巧克力(包括巧克力、代可可脂巧克力及其制品）": "糖果巧克力",
  "糖类（包括原糖、食糖、乳糖、糖浆等）": "糖类",
  "经烘焙的咖啡豆、可可豆及其制品（不包括巧克力）": "烘焙咖啡豆",
  "蔬菜及其制品（保鲜和脱水蔬菜除外）": "保鲜蔬菜",
  "粮食制品以及其它产品": "粮食制品",
  "其他杂项食品": "其他杂项",
  "冷冻水果": "冷冻水果",
  "坚果及籽类制品": "坚果制品",
  "坚果与籽类": "坚果籽类",
  "谷物制粉工业产品和麦芽": "谷物粉产",
  "饼干、糕点、面包": "饼干糕点",
  "饮料及冷冻饮品": "饮料冷饮",
  "食用油脂和油料": "油脂油料",
  "肉与肉制品": "肉与肉",
  "蛋与蛋制品": "蛋与蛋",
  "脱水蔬菜": "脱水菜",
  "茶叶类": "茶叶",
  "燕窝与燕窝制品": "燕窝",
  "食用谷物": "食用谷",
  "肠衣": "肠衣",
  "水果制品": "水果制",
  "水产品": "水产品",
  "干果": "干果",
  "乳品": "乳品",
  "保健食品": "保健食",
  "包馅面食": "包馅面",
  "调味品（不包括食糖）": "调味品",
  "调味粉": "调味粉",
  "酒类": "酒类",
  "蜂产品": "蜂产品",
};
function ciferLab(cat) { return CIFER_SHORT[cat] || cat; }

function renderCifer() {
  const c = DATA && DATA.cifer;
  const head = document.getElementById('ciferHead');
  const body = document.getElementById('ciferBody');
  if (!c || !head || !body) return;
  const cats = c.categories || [];
  const rows = c.countries || [];
  document.getElementById('ciferN').textContent = (c.total_countries != null ? c.total_countries : rows.length);
  document.getElementById('ciferDate').textContent = (c._meta && c._meta.fetched) || '--';
  head.innerHTML = '<tr><th class="c0" title="行=国别,列=CIFER品类">国别\\品类</th>' +
    cats.map(x => `<th title="${esc(x)}">${esc(ciferLab(x))}</th>`).join('') + '</tr>';
  body.innerHTML = rows.map(r => {
    const tds = cats.map(cat => {
      const n = r.cells[cat] || 0;
      const ctag = n > 0 ? 'ok' : 'none';
      return `<td data-cd="${r.code3}" data-cc="${cat}" data-n="${n}"><span class="c ${ctag}">${n > 0 ? n : '·'}</span></td>`;
    }).join('');
    const sum = Object.values(r.cells).reduce((a, b) => a + b, 0);
    return `<tr><td class="c0"><b>${r.name}</b><div class="cd">${r.code3} · ${sum} 家注册</div></td>${tds}</tr>`;
  }).join('');
  document.querySelectorAll('#ciferBody td[data-cd]').forEach(td => {
    td.addEventListener('click', () => showCiferDetail(td.dataset.cd, td.dataset.cc, td.dataset.n));
  });
}

function showCiferDetail(c3, cat, n) {
  const c = DATA && DATA.cifer;
  if (!c) return;
  const r = c.countries.find(x => x.code3 === c3);
  if (!r) return;
  const mk = c._meta && c._meta.disclaimer || '';
  document.getElementById('popT').textContent = `${r.name} · GACC 注册明细`;
  const rowHtml = c.categories.map(k => {
    const v = r.cells[k] || 0;
    return `<span class="k">${k}</span><span>${v>0 ? v+' 家在册' : '无注册记录'}</span>`;
  }).join('');
  document.getElementById('popB').innerHTML = `
    <div>当前品类 <b>${cat||'—'}</b>：<span class="c ${(+n||0)>0?'ok':'none'}">${(+n||0)>0 ? (+n)+' 家注册企业在册' : '无注册记录'}</span></div>
    <div style="margin-top:4px">国别合计 <b>${Object.values(r.cells).reduce((a,b)=>a+b,0)}</b> 家注册企业 · ${r.code3}</div>
    <div class="kv">${rowHtml}</div>
    <div style="margin-top:12px;color:var(--dim);font-size:12px">${esc(mk)}</div>`;
  document.getElementById('mask').classList.add('show');
}

load(); startAuto(); renderCifer();

/* ===== 境外企业准入名录 (CIFER 全量注册记录, 按国家) ===== */
let entDirData = null;
async function loadEntDir() {
  try {
    const r = await fetch(API_BASE + '/cifer_enterprises_all.json?t=' + Date.now(), { cache: 'no-store' });
    const j = await r.json();
    // 合并每国 records, 按 appSeqNo 去重
    const seen = {}, out = [];
    for (const [k, v] of Object.entries(j)) {
      for (const rec of (v.records || [])) {
        if (!rec.appSeqNo || seen[rec.appSeqNo]) continue;
        seen[rec.appSeqNo] = 1;
        out.push(rec);
      }
    }
    entDirData = { records: out, countriesDone: Object.keys(j).length, updated: new Date().toLocaleDateString('zh-CN') };
    renderEntDir();
  } catch {
    const el = document.getElementById('entDirBody');
    if (el) el.innerHTML = '<div class="dim">名录暂无数据 — 全量抓取进行中，稍后重载。</div>';
  }
}
function renderEntDir() {
  const el = document.getElementById('entDirBody');
  if (!entDirData || !entDirData.records.length) { el.innerHTML = '<div class="dim">名录加载中…</div>'; loadEntDir(); return; }
  const recs = entDirData.records;
  // 汇总统计
  const st = {}; recs.forEach(r => st[r.statusName] = (st[r.statusName]||0)+1);
  document.getElementById('entDirCount').textContent = recs.length;
  document.getElementById('entDirAll').textContent = '158';
  document.getElementById('entDirCov').textContent = entDirData.countriesDone;
  document.getElementById('entDirDate').textContent = entDirData.updated;
  const nb = document.getElementById('entDirN'); if (nb) nb.textContent = recs.length;
  // 按 状态>品类 排序
  const stOrd = { '有效':0, '暂停进口':1, '注销':2, '撤销':3 };
  recs.sort((a,b) => (stOrd[a.statusName]??9)-(stOrd[b.statusName]??9) || (a.registerTypeName||'').localeCompare(b.registerTypeName||'') || a.country.localeCompare(b.country));
  const stChip = s => s==='有效' ? 'ok' : (s==='暂停进口' ? 'part' : 'pause');
  el.innerHTML = `
    <div style="display:flex;gap:14px;margin-bottom:10px;flex-wrap:wrap">
      ${Object.entries(st).map(([k,v]) => `<span class="c ${stChip(k)}" style="display:inline-block">${k} ${v}</span>`).join('')}
      <span class="dim" style="margin-left:auto">按 状态 → 品类 → 国别 排序 · 点击行看企业详情</span>
    </div>
    <div style="max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:8px">
      <table style="border-collapse:collapse;width:100%;font-size:12px">
        <thead style="position:sticky;top:0;background:#f7f9fc">
          <tr>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px;text-align:left">企业</th>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px">国家</th>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px">品类</th>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px">注册编号</th>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px">关区</th>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px">状态</th>
            <th style="border-bottom:1px solid var(--line);padding:7px 9px">有效期至</th>
          </tr>
        </thead>
        <tbody>
          ${recs.map(r => `<tr data-app="${esc(r.appSeqNo)}" style="cursor:pointer">
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(r.enterpriseAddress||'')}"><b>${esc(r.enterpriseName||'')}</b></td>
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;text-align:center">${esc(r.countryName||r.country||'')}</td>
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;text-align:center">${esc(r.registerTypeName||'')}</td>
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;text-align:center;font-size:11px;color:var(--dim)">${esc(r.appSeqNo||'')}</td>
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;text-align:center">${esc(r.orgNo||'')}</td>
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;text-align:center"><span class="c ${stChip(r.statusName)}" style="display:inline-block">${esc(r.statusName||'')}</span></td>
            <td style="border-bottom:1px solid var(--line);padding:6px 9px;text-align:center;font-size:11px">${esc(r.endDate||'')}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  el.querySelectorAll('tr[data-app]').forEach(tr => tr.addEventListener('click', () => showEntDetail(tr.dataset.app)));
}
function showEntDetail(appNo) {
  const r = entDirData.records.find(x => x.appSeqNo === appNo);
  if (!r) return;
  const stChip = s => s==='有效' ? 'ok' : (s==='暂停进口' ? 'part' : 'pause');
  document.getElementById('popT').textContent = 'CIFER 注册记录';
  document.getElementById('popB').innerHTML = `
    <div style="font-size:14px;line-height:1.6"><b>${esc(r.enterpriseName||'')}</b></div>
    <div class="kv" style="margin-top:10px">
      <span class="k">国家/地区</span><span>${esc(r.countryName||r.country||'')}（${esc(r.country||'')}）</span>
      <span class="k">注册品类</span><span>${esc(r.registerTypeName||'')} <span class="dim">(${esc(r.registerType||'')})</span></span>
      <span class="k">注册号</span><span>${esc(r.appSeqNo||'')} · ${esc(r.regCo||'')}</span>
      <span class="k">主管关区</span><span>${esc(r.orgNo||'—')}</span>
      <span class="k">状态</span><span class="c ${stChip(r.statusName)}" style="display:inline-block">${esc(r.statusName||'')}</span>
      <span class="k">注册日</span><span>${esc(r.startDate||r.regDate||'—')}</span>
      <span class="k">有效期至</span><span>${esc(r.endDate||r.availDate||'—')}</span>
      <span class="k">企业地址</span><span>${esc(r.enterpriseAddress||'—')}</span>
      <span class="k">省份/地区</span><span>${esc(r.province||'—')}</span>
      <span class="k">登记时间</span><span>${esc(r.addTime||'—')}</span>
    </div>
    <div style="margin-top:12px;color:var(--dim);font-size:11.5px">来源：GACC 单一窗口 CIFER 境外生产企业注册公开库（ciferquery.singlewindow.cn）· 280 号令</div>`;
  document.getElementById('mask').classList.add('show');
}
loadEntDir();
