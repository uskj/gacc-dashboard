# -*- coding: utf-8 -*-
"""重建 query.json v2: 三源口径
1. GACC 官方附件 (gacc_official.json) - 权威准入名单
2. chinaport 企业注册矩阵 (chinaport_matrix.json) - 辅证
3. 禁止输入明细 (_gacc_banned.json) - 国家×动物 粒度, 不再全局 banned=true
"""
import json, io, sys, os
from collections import OrderedDict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r'D:\Projects\gacc_dashboard_site\data'

off = json.load(open(os.path.join(BASE, 'gacc_official.json'), encoding='utf-8'))
cpm = json.load(open(os.path.join(BASE, 'chinaport_matrix.json'), encoding='utf-8'))
bn = json.load(open(os.path.join(BASE, '_gacc_banned.json'), encoding='utf-8'))

def norm(s):
    return (s or '').strip()

# GACC 官方: 品类 -> 国家集合
off_cats = OrderedDict()
for k, v in off.items():
    if k == 'banned':
        continue
    cat = v.get('品类', k)
    off_cats[cat] = set(norm(x) for x in v.get('国家', []) if norm(x))

# 禁止输入明细: 国家 -> [动物条目]
country_to_banned = bn.get('country_to_banned', {})
banned_detail = bn.get('banned_detail', [])

# chinaport
cc_map = cpm.get('cc_map', {})
cp_cat_country = cpm.get('cat_country', {})
cp_country_cat = cpm.get('country_cat', {})
name2code = {norm(name): code for code, name in cc_map.items()}

# 国别全集 = GACC 官方 ∪ chinaport ∪ 禁止表
all_names = set()
for cset in off_cats.values():
    all_names |= cset
for code in cp_country_cat:
    if code in cc_map:
        all_names.add(norm(cc_map[code]))
for cname in country_to_banned:
    all_names.add(norm(cname))

countries = OrderedDict()
for name in sorted(all_names):
    code = name2code.get(name, '')
    official = sorted(cat for cat, cset in off_cats.items() if name in cset)
    cp_cats = []
    if code:
        for cat, n in (cp_country_cat.get(code, {}) or {}).items():
            if n > 0:
                cp_cats.append(cat)
    banned_animals = [b['animals'] for b in banned_detail if norm(b.get('country', '')) == name]
    if not banned_animals:
        banned_animals = country_to_banned.get(name, [])
    countries[code or name] = {
        'name': name,
        'code': code or '',
        'official': official,
        'cifer': sorted(cp_cats),
        'banned_animals': banned_animals,
    }

# 品类 -> 国
all_cat_names = set(off_cats.keys()) | set(cp_cat_country.keys())
categories = OrderedDict()
for cat in sorted(all_cat_names):
    off_countries = sorted(off_cats.get(cat, set()))
    cp_countries = []
    for ccode, n in (cp_cat_country.get(cat, {}) or {}).items():
        if n > 0 and ccode in cc_map:
            cp_countries.append({'name': norm(cc_map[ccode]), 'code': ccode, 'n': n})
    categories[cat] = {
        'official': off_countries,
        'cifer': cp_countries,
        'total': len(off_countries),
        'note': 'cifer 为注册辅证(采样上限), official 为准入国家数',
    }

out = {
    '_meta': {
        'sources': {
            'official': 'GACC 总署官网附件 (dzs.customs.gov.cn, 2026-08~2026-10 更新, 9 份 xlsx/doc)',
            'chinaport': 'chinaport 进境动植物境外企业检疫注册登记系统 (scintl.chinaport.gov.cn, 2026-10-11)',
            'banned': 'GACC 禁止从动物疫病流行国家地区输入的动物及其产品一览表 (2026-10-03 更新, 154 国 525 条)',
        },
        'links': [
            'http://dzs.customs.gov.cn/dzs/2020-05/19/article_2025123119301257348.html',
            'http://dzs.customs.gov.cn/dzs/2022-07/01/article_2025123119301238272.html',
            'http://jckspj.customs.gov.cn/spj/xxfw39/fhpgscyqjyctmydgjhdqshspml/index.html',
            'http://scintl.chinaport.gov.cn/aprwebserver/pages/apr/public/html/companyList.html',
            'http://dzs.customs.gov.cn/dzs/2018-05/15/article_2025123119301285807.html',
        ],
        'rule': 'official = GACC 官方准入名单; cifer = 在册注册辅证; banned_animals = 逐国禁止动物(疫病), 非全品全禁',
        'generated': '2026-10-11',
        'official_cats': len(off_cats),
        'banned_countries': bn.get('total_countries', 0),
        'banned_entries': bn.get('total_animal_entries', 0),
    },
    'countries': countries,
    'categories': categories,
    'banned_detail': banned_detail,
}
json.dump(out, open(os.path.join(BASE, 'query.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('written query.json')
print('countries:', len(countries), 'categories:', len(categories))
print('有 banned_animals 的国:', sum(1 for v in countries.values() if v['banned_animals']))
print('有 official 准入的国:', sum(1 for v in countries.values() if v['official']))
