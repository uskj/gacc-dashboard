# -*- coding: utf-8 -*-
"""合并多源生成独立查询页数据 querydata.json
v2: 全量 158 国(用记录自带 countryName) + 别名统一(消重) + CIFER registerType→品类 + 记录数断言
"""
import json, io, sys, os
from collections import defaultdict, OrderedDict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r'D:\Projects\gacc_dashboard_site\data'
def L(n): return json.load(open(os.path.join(BASE, n), encoding='utf-8'))

off = L('gacc_official.json'); restrict = L('_gacc_restricted.json')
cpm = L('chinaport_matrix.json'); cifer = L('cifer_enterprises_all.json')
bn = L('_gacc_banned.json'); comp4 = L('_4countries_companies.json')
pindex = L('_products_index.json')['products']

cc_map = {k: v.strip() for k, v in cpm.get('cc_map', {}).items()}   # num -> cn
name2num = {v: k for k, v in cc_map.items()}
cp_country = cpm.get('country_cat', {})   # num -> {子类: n}

# ---- 别名: 原始名 -> cc_map 规范名 (统一重复国家条目, 如 俄罗斯 vs 俄罗斯联邦) ----
ALIAS = {
    '俄罗斯': '俄罗斯联邦', '塞尔维亚': '塞尔维亚共和国', '北马其顿': '北马其顿共和国',
    '黑山': '黑山共和国', '孟加拉国': '孟加拉', '蒙古国': '蒙古', '多米尼加共和国': '多米尼加',
    '波多黎各(美属)': '波多黎各', '开曼群岛（英属）': '开曼群岛', '开曼群岛(英属)': '开曼群岛',
    '刚果(布)': '刚果（布）', '刚果(金)': '刚果（金）', '刚果民主共和国': '刚果（金）',
    '密克罗尼西亚联邦': '密克罗尼西亚(联邦)', '波黑': '波斯尼亚和黑塞哥维那',
    '北马里亚纳群岛': '北马里亚纳自由联邦',
}
def canon(n):
    n = (n or '').strip()
    return ALIAS.get(n, n)

# ---- 官方: 品类 -> {规范国名: 状态}
off_cat = OrderedDict()
for k, v in off.items():
    if k == 'banned':
        continue
    cat = v.get('品类', k)
    sm = {canon(c): '准入' for c in v.get('国家', [])}
    for cname, r in (restrict.get(k, {}) or {}).items():
        cn = canon(cname)
        if cn in sm:
            sm[cn] = r
    off_cat[cat] = sm
off_country = defaultdict(dict)
for cat, sm in off_cat.items():
    for cname, st in sm.items():
        off_country[cname][cat] = st

# ---- 企业明细 (按规范国名聚合) ----
def parse_cp(rows):
    out = []
    for r in rows:
        nm = (r.get('corpNameEn') or '').strip() or (r.get('corpNameMo') or '').strip()
        out.append({
            'cat': (r.get('prodTypeNameCn') or '').strip(),
            'sub': (r.get('prodCategoryNameCn') or '').strip(),
            'prod': (r.get('prodNameCn') or '').strip(),
            'name': nm, 'regNo': r.get('chinaRegNo') or '',
            'type': (r.get('corpTypeNameCn') or '').strip()[:30],
            'validTo': r.get('validTo') or '', 'src': 'chinaport',
        })
    return out

ent = defaultdict(list)
for cname, blk in comp4.items():
    ent[canon(cname)].extend(parse_cp(blk.get('rows', [])))

cifer_total = 0
cifer_cat = defaultdict(lambda: defaultdict(int))
for iso, blk in cifer.items():
    recs = blk.get('records', []) if isinstance(blk, dict) else blk
    for r in recs:
        cifer_total += 1
        cn = canon(r.get('countryName'))
        rt = (r.get('registerTypeName') or '').strip()
        ent[cn].append({
            'cat': 'CIFER', 'sub': rt or '', 'prod': '',
            'name': r.get('enterpriseName') or '', 'regNo': r.get('appSeqNo') or '',
            'type': r.get('statusName') or '', 'validTo': r.get('endDate') or '', 'src': 'CIFER',
        })
        if rt:
            num = name2num.get(cn, '')
            cifer_cat[rt][num or cn] += 1

banned_cn = {canon(k): v for k, v in bn.get('country_to_banned', {}).items()}

# ---- 国家全集 ----
all_names = set(off_country) | set(banned_cn) | set(ent) | {'萨摩亚', '瓦努阿图'}
for num in cp_country:
    if num in cc_map:
        all_names.add(cc_map[num])

countries = OrderedDict()
for cname in sorted(all_names):
    num = name2num.get(cname, '')
    oc = off_country.get(cname, {})
    # 去重 (src+regNo+name)
    seen, ded = set(), []
    for x in ent.get(cname, []):
        k = (x['src'], x['regNo'], x['name'])
        if k in seen:
            continue
        seen.add(k); ded.append(x)
    cp_cats = {}
    if num:
        for sub, n in (cp_country.get(num, {}) or {}).items():
            if n > 0:
                cp_cats[sub] = n
    if not cp_cats and ded:
        for x in ded:
            kk = x.get('sub') or x.get('cat') or '其他'
            if kk:
                cp_cats[kk] = cp_cats.get(kk, 0) + 1
    b = banned_cn.get(cname, [])
    countries[cname] = {
        'name': cname, 'num': num, 'official': oc,
        'cifer_reg': cp_cats, 'enterprises': ded,
        'banned': b, 'blank': not oc and not ded and not b,
    }

# ---- 品类全集 ----
categories = OrderedDict()
for cat, sm in off_cat.items():
    categories[cat] = {'official': sorted(sm.keys()), 'status': sm,
                       'cifer': {}, 'n_official': len(sm), 'src': 'official'}
sub_country = defaultdict(dict)
for num, subs in cp_country.items():
    for sub, n in subs.items():
        if n > 0:
            sub_country[sub][num] = n
for sub, cc in sub_country.items():
    c = categories.setdefault(sub, {'official': [], 'status': {}, 'cifer': {},
                                    'n_official': 0, 'src': 'chinaport'})
    if not c['cifer']:
        c['cifer'] = dict(sorted(cc.items(), key=lambda x: -x[1]))
# CIFER registerType -> 品类 (补齐肉类/乳品/水产等)
for rt, cc in cifer_cat.items():
    c = categories.setdefault(rt, {'official': [], 'status': {}, 'cifer': {},
                                   'n_official': 0, 'src': 'cifer'})
    for k, v in cc.items():
        c['cifer'][k] = c['cifer'].get(k, 0) + v

# ---- 校验: 任何 CIFER 明细都不得丢失 ----
placed = {x['src'] for v in countries.values() for x in v['enterprises']}
cifer_placed = sum(1 for v in countries.values() for e in v['enterprises'] if e['src'] == 'CIFER')
assert cifer_placed == cifer_total, f'CIFER 明细丢失: placed={cifer_placed} total={cifer_total}'
assert 'CIFER' in placed, 'CIFER 企业未入册'

out = {
    '_meta': {
        'generated': '2026-10-12',
        'sources': {
            '官方准入': 'GACC 总署附件 9 份 · 8 大类 (2026-08~10)',
            'chinaport': 'chinaport 进境动植物境外企业检疫注册登记',
            'CIFER': 'GACC 单一窗口境外食品生产企业注册 (全 158 国)',
            '疫病禁止': 'GACC 禁止输入动物一览表 154 国 525 条 (2026-10-03)',
        },
        'links': [
            'http://dzs.customs.gov.cn/dzs/2020-05/19/article_2025123119301257348.html',
            'http://dzs.customs.gov.cn/dzs/2022-07/01/article_2025123119301238272.html',
            'http://scintl.chinaport.gov.cn/aprwebserver/pages/apr/public/html/companyList.html',
            'http://dzs.customs.gov.cn/dzs/2018-05/15/article_2025123119301285807.html',
        ],
        'n_countries': len(countries), 'n_categories': len(categories),
        'n_products': len(pindex),
    },
    'cc_map': cc_map, 'name2num': name2num,
    'countries': countries, 'categories': categories,
    'products': pindex,
}
json.dump(out, open(os.path.join(BASE, 'querydata.json'), 'w', encoding='utf-8'), ensure_ascii=False)

print('cifer_total=%d cifer_placed=%d' % (cifer_total, cifer_placed))
print('countries:', len(countries), 'categories:', len(categories), 'products:', len(pindex))
n_ent = sum(len(c['enterprises']) for c in countries.values())
print('enterprises total:', n_ent)
for probe in ['墨西哥', '巴西', '俄罗斯联邦', '美国', '印度', '阿根廷', '巴布亚新几内亚', '萨摩亚']:
    v = next((c for c in countries.values() if c['name'] == probe), None)
    if v:
        print('  %s: num=%s official=%d cp_reg=%d ent=%d banned=%d' %
              (probe, v['num'], len(v['official']), len(v['cifer_reg']), len(v['enterprises']), len(v['banned'])))
    else:
        print('  %s: 缺' % probe)
