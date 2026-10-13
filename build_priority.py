# -*- coding: utf-8 -*-
"""
生成"需准入企业优先级总榜"数据：国家级三源加权。
三源：
  1. GACC 官方准入品类数（query.json countries[].official 里 status=='准入' 的品类数）— 权重 40%
  2. CIFER 在册注册企业数 — 权重 30%
     （cifer_enterprises_all.json，口径：仅 statusName=='有效'，且企业名归一化后去重，
       排除同企业多品类/多产品的重复注册编号，排除注销与暂停进口）
  3. 对华进口额（UN Comtrade，latest.json verifiedLeads2025 / countries[].imports）— 权重 30%
输出 data/priority_board.json
"""
import json, math, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')

def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)

def norm_ent_name(n):
    return re.sub(r'\s+', ' ', str(n or '')).strip().upper()

q = load('query.json')
cf = load('cifer_enterprises_all.json')
latest = load('latest.json')

# --- 源1：官方准入品类数 ---
official_count = {}   # query country code (ISO数字/别名) -> 准入品类数
official_total = {}
for code, c in q['countries'].items():
    off = c.get('official') or {}
    if isinstance(off, dict):
        acc = sum(1 for st in off.values() if st == '准入')
        official_count[code] = acc
        official_total[code] = len(off)
    else:
        official_count[code] = len(off)
        official_total[code] = len(off)

# --- 源2：CIFER 在册企业数（有效 & 企业名去重） ---
cifer_cnt = {}        # cifer 国家键 -> 有效在册企业数（企业名归一化去重）
cifer_name = {}
for k, v in cf.items():
    recs = v.get('records') or []
    if not recs:
        continue
    seen = set()
    for r in recs:
        if r.get('status') or r.get('statusName'):
            st = r.get('statusName') or ''
            if st and st != '有效':
                continue
        nm = norm_ent_name(r.get('enterpriseName'))
        if nm:
            seen.add(nm)
    cifer_cnt[k] = len(seen)
    cifer_name[k] = recs[0].get('countryName') or k

# 把 cifer 国家键 映射到 国家名（中文）
cifer_by_name = {}
for k, n in cifer_name.items():
    if n:
        cifer_by_name.setdefault(n, k)

# --- 源3：进口额 + leadPriority ---
import_by_iso3 = {}   # ISO3 国家码 -> totalUSD
import_tier = {}
vl = latest.get('verifiedLeads2025') or {}
for iso3, v in vl.items():
    import_by_iso3[iso3] = v.get('totalUSD') or 0
    lp = v.get('leadPriority') or {}
    import_tier[iso3] = lp.get('tier') or ''
# 也取 latest.countries[].imports（若存在）
for c in (latest.get('countries') or []):
    iso3 = c.get('code')
    imp = c.get('imports') or {}
    if iso3 and (imp.get('totalUSD') or 0) > (import_by_iso3.get(iso3) or 0):
        import_by_iso3[iso3] = imp.get('totalUSD') or 0
    lp = c.get('leadPriority') or {}
    if lp.get('tier'):
        import_tier[iso3] = lp.get('tier')

# --- 三源匹配：把 query 国家 (中文名+code) 关联到 cifer 键 与 进口额 iso3 ---
rows = []
# 建立 中文名 -> cifer键、中文名 -> iso3
q_by_name = {c['name']: (code, c) for code, c in q['countries'].items()}

for name, (qcode, qc) in q_by_name.items():
    off_acc = official_count.get(qcode, 0)
    off_tot = official_total.get(qcode, 0)
    if off_acc <= 0:
        continue  # 无官方准入品类 → 不算"需准入"
    # cifer：按国家名匹配
    cifer_key = cifer_by_name.get(name)
    ent = cifer_cnt.get(cifer_key, 0) if cifer_key else 0
    if ent <= 0:
        continue  # 总榜只列"有在册注册 + 有官方准入"的国家
    # 进口额：query code 多为 ISO数字码或别名；cifer 键为 ISO3字母码。
    # 通过 latest.countries (code=ISO2/ISO3) 反查：找 name 对应的 iso
    iso3 = None
    for c in (latest.get('countries') or []):
        if c.get('name') == name:
            iso3 = c.get('code')
            break
    imp = import_by_iso3.get(iso3, 0) if iso3 else 0
    tier = import_tier.get(iso3, '') if iso3 else ''
    rows.append({
        'name': name,
        'qcode': qcode,
        'iso3': iso3 or '',
        'official': off_acc,
        'official_total': off_tot,
        'enterprises': ent,
        'import_usd': imp,
        'tier': tier,
        'import_note': ('已核 2025 对华进口额' if imp > 0 else ('未取到进口额(配额/缺)' if not iso3 else '有数据但为0')),
    })

# --- 归一化 + 加权 ---
max_off = max((r['official'] for r in rows), default=1) or 1
max_ent = max((r['enterprises'] for r in rows), default=1) or 1
max_imp = max((r['import_usd'] for r in rows), default=1) or 1

def norm_ent(v):
    # 企业数用 log10 归一，避免印度/法国等超大值碾压
    if v <= 0:
        return 0.0
    return min(1.0, math.log10(v + 1) / math.log10(max_ent + 1))

def norm_imp(v):
    if v <= 0:
        return 0.0
    return min(1.0, math.log10(v + 1) / math.log10(max_imp + 1))

for r in rows:
    s_off = r['official'] / max_off
    s_ent = norm_ent(r['enterprises'])
    s_imp = norm_imp(r['import_usd'])
    # leadPriority tier 加成：A/B 级 → 进口意向分上浮
    boost = 0.0
    t = r['tier'] or ''
    if t.startswith('A'):
        boost = 0.15
    elif t.startswith('B'):
        boost = 0.08
    r['s_off'] = round(s_off, 3)
    r['s_ent'] = round(s_ent, 3)
    r['s_imp'] = round(min(1.0, s_imp + boost), 3)
    score = 0.40 * s_off + 0.30 * s_ent + 0.30 * min(1.0, s_imp + boost)
    r['score'] = round(score * 100, 1)
    # 分级
    if r['score'] >= 70:
        r['grade'] = 'A'
    elif r['score'] >= 50:
        r['grade'] = 'B'
    elif r['score'] >= 30:
        r['grade'] = 'C'
    else:
        r['grade'] = 'D'

rows.sort(key=lambda x: (-x['score'], -x['enterprises']))

out = {
    '_meta': {
        'generated': '2026-10-13',
        'method': '三源加权：官方准入品类(40%) × CIFER在册有效企业数(30%,企业名去重,log归一) × 对华进口额(30%,log归一+leadPriority加成)',
        'weights': {'official': 0.40, 'enterprises': 0.30, 'import': 0.30},
        'cifer_mix': 'count of statusName==有效 records with normalized enterpriseName dedup',
        'n_countries': len(rows),
        'n_with_import': sum(1 for r in rows if r['import_usd'] > 0),
        'n_with_enterprises': sum(1 for r in rows if r['enterprises'] > 0),
    },
    'board': rows,
}
with open(os.path.join(DATA, 'priority_board.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print('n rows:', len(rows))
print('n with import:', out['_meta']['n_with_import'])
print('n with enterprises:', out['_meta']['n_with_enterprises'])
for r in rows[:10]:
    print(f"  {r['grade']} {r['score']:>5}  {r['name']:<10} 官方{r['official']:>2}/{r['official_total']:<3} 企业{r['enterprises']:>4} 进口${r['import_usd']/1e6:>8.0f}M tier={r['tier']}")
