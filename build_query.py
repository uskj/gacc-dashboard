# -*- coding: utf-8 -*-
"""从 cifer_enterprises_all.json 派生双向查询数据 query.json
国 -> 品类(有效注册数) ; 品类 -> 国(有效注册数)
仅统计 statusName == '有效' 的记录, 按 appSeqNo 去重
"""
import json, io, sys, os
from collections import OrderedDict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r'D:\Projects\gacc_dashboard_site\data'
raw = json.load(open(os.path.join(BASE, 'cifer_enterprises_all.json'), encoding='utf-8'))

# 国家块: code3 -> {countryName, records[]}. 去重 + 只取有效
seen = set()
countries = OrderedDict()   # code3 -> {'name':cn, 'cats': {cat: n}}
cat_index = {}               # cat -> {code3: n}
tot_active = 0
for code, block in raw.items():
    c = countries.setdefault(code, {'name': None, 'cats': OrderedDict()})
    for r in block.get('records', []):
        cn = r.get('countryName')
        if cn:
            c['name'] = cn
        if r.get('statusName') != '有效':
            continue
        app = r.get('appSeqNo')
        key = (code, app)
        if app and key in seen:
            continue
        seen.add(key)
        tot_active += 1
        cat = r.get('registerTypeName', '?')
        c['cats'][cat] = c['cats'].get(cat, 0) + 1
        cat_index.setdefault(cat, {})[code] = cat_index.get(cat, {}).get(code, 0) + 1

# 只保留有有效记录的国家/品类
countries = {k: v for k, v in countries.items() if v['cats']}
for v in countries.values():
    v['cats'] = OrderedDict(sorted(v['cats'].items(), key=lambda x: -x[1]))
cat_index = {k: OrderedDict(sorted(v.items(), key=lambda x: -x[1])) for k, v in cat_index.items()}

out = {
    '_meta': {
        'source': 'cifer_enterprises_all.json (CIFER 全量企业)',
        'rule': '仅计 statusName=有效, 按 appSeqNo 去重; 有有效注册 = 该国该品类准入',
        'total_active': tot_active,
        'total_countries': len(countries),
        'total_categories': len(cat_index),
    },
    'countries': countries,
    'categories': {k: {'countries': v, 'total': sum(v.values())} for k, v in cat_index.items()},
}
path = os.path.join(BASE, 'query.json')
json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
print('written', path)
print('countries:', len(countries), 'cats:', len(cat_index), 'active:', tot_active)
print('top cats:', list(list(cat_index.items())[:0] or []))
for k, v in sorted(cat_index.items(), key=lambda x: -x[1]['total'])[:10]:
    print(f'  {k}: {v["total"]} 家 / {len(v["countries"])} 国')
