# -*- coding: utf-8 -*-
"""合并 4 源生成独立查询页数据 querydata.json"""
import json, io, sys, os
from collections import defaultdict, OrderedDict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r'D:\Projects\gacc_dashboard_site\data'

off = json.load(open(os.path.join(BASE, 'gacc_official.json'), encoding='utf-8'))
restrict = json.load(open(os.path.join(BASE, '_gacc_restricted.json'), encoding='utf-8'))
cpm = json.load(open(os.path.join(BASE, 'chinaport_matrix.json'), encoding='utf-8'))
cifer = json.load(open(os.path.join(BASE, 'cifer_enterprises_all.json'), encoding='utf-8'))
bn = json.load(open(os.path.join(BASE, '_gacc_banned.json'), encoding='utf-8'))
comp4 = json.load(open(os.path.join(BASE, '_4countries_companies.json'), encoding='utf-8'))
pindex = json.load(open(os.path.join(BASE, '_products_index.json'), encoding='utf-8'))['products']

cc_map = {k: v.strip() for k, v in cpm.get('cc_map', {}).items()}   # num -> cn
name2num = {v: k for k, v in cc_map.items()}
cp_country = cpm.get('country_cat', {})   # num -> {子类: n}
cp_cat = cpm.get('cat_country', {})       # 子类 -> {num: n} (多为空, 用 country_cat 反推)

# ---- 官方: 品类 -> {国名: 状态}
off_cat = OrderedDict()
for k, v in off.items():
    if k == 'banned':
        continue
    cat = v.get('品类', k)
    sm = {c.strip(): '准入' for c in v.get('国家', [])}
    for cname, r in (restrict.get(k, {}) or {}).items():
        if cname in sm:
            sm[cname] = r
    off_cat[cat] = sm

off_country = defaultdict(dict)
for cat, sm in off_cat.items():
    for cname, st in sm.items():
        off_country[cname][cat] = st

# ---- 企业明细
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

iso2name = {'MEX': '墨西哥', 'PNG': '巴布亚新几内亚', 'SLB': '所罗门群岛', 'WSM': '萨摩亚',
            'VUT': '瓦努阿图', 'BRA': '巴西', 'KAZ': '哈萨克斯坦', 'ARG': '阿根廷',
            'VNM': '越南', 'FRA': '法国', 'USA': '美国', 'ESP': '西班牙', 'IDN': '印度尼西亚',
            'THA': '泰国', 'NLD': '荷兰', 'GBR': '英国', 'ITA': '意大利', 'DEU': '德国'}
enterprises = defaultdict(list)
for cname, blk in comp4.items():
    code = blk.get('code', '')
    enterprises[code].extend(parse_cp(blk.get('rows', [])))
for iso, recs in cifer.items():
    cname = iso2name.get(iso, '')
    num = name2num.get(cname, '')
    if not num:
        continue
    for r in recs.get('records', []):
        enterprises[num].append({
            'cat': 'CIFER', 'sub': r.get('registerTypeName') or '', 'prod': '',
            'name': r.get('enterpriseName') or '', 'regNo': r.get('appSeqNo') or '',
            'type': r.get('statusName') or '', 'validTo': r.get('endDate') or '', 'src': 'CIFER',
        })

banned_cn = bn.get('country_to_banned', {})

# 空白国 (无官方/无注册/不在疫病表, 但用户会查) 显式补入
BLANK = ['萨摩亚', '瓦努阿图']

# 国家全集
all_names = set(off_country.keys()) | set(banned_cn.keys()) | set(BLANK)
for num in cp_country:
    if num in cc_map:
        all_names.add(cc_map[num])

countries = OrderedDict()
for cname in sorted(all_names):
    num = name2num.get(cname, '')
    oc = off_country.get(cname, {})
    ent = enterprises.get(num, [])
    # cifer_reg: 优先用矩阵, 缺失则从企业明细统计
    cp_cats = {}
    if num:
        for sub, n in (cp_country.get(num, {}) or {}).items():
            if n > 0:
                cp_cats[sub] = n
    if not cp_cats and ent:
        for e in ent:
            key = e.get('sub') or e.get('cat') or '其他'
            cp_cats[key] = cp_cats.get(key, 0) + 1
    countries[num or cname] = {
        'name': cname, 'num': num, 'official': oc,
        'cifer_reg': cp_cats, 'enterprises': ent,
        'banned': banned_cn.get(cname, []),
        'blank': not oc and not ent and not banned_cn.get(cname, []),
    }

# 品类全集
categories = OrderedDict()
for cat, sm in off_cat.items():
    categories[cat] = {'official': sorted(sm.keys()), 'status': sm,
                        'cifer': {}, 'n_official': len(sm), 'src': 'official'}
# chinaport 子类 -> 国
sub_country = defaultdict(dict)
for num, subs in cp_country.items():
    for sub, n in subs.items():
        if n > 0:
            sub_country[sub][num] = n
for sub, cc in sub_country.items():
    categories.setdefault(sub, {'official': [], 'status': {}, 'cifer': {},
                                'n_official': 0, 'src': 'chinaport'})
    categories[sub]['cifer'] = dict(sorted(cc.items(), key=lambda x: -x[1]))

out = {
    '_meta': {
        'generated': '2026-10-11',
        'sources': {
            '官方准入': 'GACC 总署附件 9 份 · 8 大类 (2026-08~10)',
            'chinaport': 'chinaport 进境动植物境外企业检疫注册登记',
            'CIFER': 'GACC 单一窗口境外生产企业注册',
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
print('countries:', len(countries), 'categories:', len(categories))
for probe in ['墨西哥', '巴布亚新几内亚', '所罗门群岛', '萨摩亚', '瓦努阿图']:
    v = next((c for c in countries.values() if c['name'] == probe), None)
    print(f'  {probe}: official={list(v["official"].keys())} cp={len(v["cifer_reg"])} ent={len(v["enterprises"])} banned={len(v["banned"])}' if v else f'  {probe}: 缺')
