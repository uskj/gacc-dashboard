# -*- coding: utf-8 -*-
"""从 GACC 官方附件提取 (产品 -> 国家) 索引, 输出 _products_index.json"""
import io, sys, os, glob, re, json, openpyxl, docx
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
D = r'D:\Projects\gacc_dashboard_site\data'
SPLIT = re.compile(r'[、，,;；\n]')
ALIAS = {
    '吉尔吉斯共和国': '吉尔吉斯斯坦', '安巴': '安提瓜和巴布达',
    '阿拉伯联合酋长国': '阿联酋', '刚果（布）': '刚果(布)', '刚果（金）': '刚果(金)',
    '国家（地区）': '', '国家': '',
}

def clean(x):
    return re.sub(r'\s+', '', str(x or '')).strip()

def split_countries(s):
    out = []
    for x in SPLIT.split(clean(s)):
        x = x.strip('。. ')
        x = re.sub(r'[（(].*?[）)]', '', x).strip()   # 去括号注解
        x = ALIAS.get(x, x)
        if x and len(x) <= 14 and x not in ('国家', '地区', '国家/地区') and '：' not in x and '种类' not in x:
            out.append(x)
    return out

def split_products(s):
    """自由文本产品名 -> 列表: 去掉括号内拉丁/英文, 保留中文产品名"""
    s = str(s or '')
    parts = re.split(r'[、，,]', s)
    out = []
    for p in parts:
        p = re.sub(r'[（(].*?[）)]', '', p)   # 去括号
        p = clean(p)
        if p and len(p) <= 20:
            out.append(p)
    return out

prod_country = defaultdict(set)   # 产品 -> {国家}
src_note = {}

def norm_c(x):
    x = clean(x)
    x = ALIAS.get(x, x)
    x = re.sub(r'[（(].*?[）)]', '', x).strip()
    x = ALIAS.get(x, x)
    if x in ('国家', '地区', '国家/地区'): return ''
    return x

def add(prod, countries):
    prod = clean(prod)
    if not prod: return
    for c in countries:
        c = norm_c(c)
        if c: prod_country[prod].add(c)

# 1. 新鲜蔬菜 xlsx: 产品名, 国家
f = glob.glob(os.path.join(D, '_gacc_*新鲜蔬菜*.xlsx'))[0]
wb = openpyxl.load_workbook(f, read_only=True)
ws = wb.worksheets[0]
rows = list(ws.iter_rows(values_only=True))
cur_prod = None
for row in rows[2:]:
    p, c = row[0], row[1]
    if p and str(p).startswith('='):
        p = None
    if p: cur_prod = clean(p)
    if cur_prod and c:
        add(cur_prod, split_countries(c))
src_note['新鲜蔬菜/调味料'] = len(rows)

# 2. 允许进口饲料 xlsx: 国家, 产品类别(可多行)
f = glob.glob(os.path.join(D, '_gacc_*允许进口饲料*.xlsx'))[0]
wb = openpyxl.load_workbook(f, read_only=True)
ws = wb.worksheets[0]
cur_country = None
for row in list(ws.iter_rows(values_only=True))[2:]:
    c, p = row[1], row[2]
    if c and clean(c) not in ('亚洲', '欧洲', '非洲', '美洲', '大洋洲') and not clean(c).isdigit():
        cur_country = clean(c)
    if cur_country and p:
        for line in str(p).split('\n'):
            pl = clean(line)
            if pl: add(pl, [cur_country])

# 3. 非食用动物产品 xlsx: 国家, 产品
f = glob.glob(os.path.join(D, '_gacc_*非食用动物*.xlsx'))[0]
wb = openpyxl.load_workbook(f, read_only=True)
ws = wb.worksheets[0]
cur_c = None
for row in list(ws.iter_rows(values_only=True))[2:]:
    c, p = row[0], row[1]
    if c and clean(c) not in ('亚洲', '欧洲', '非洲', '美洲', '大洋洲', '北美洲', '南美洲') and c != '洲别':
        cur_c = clean(c)
    if cur_c and p:
        add(clean(p), [cur_c])

# 4. 水生动物 xlsx: 国家, 类别/品种 (多 sheet)
f = glob.glob(os.path.join(D, '_gacc_*水生动物*.xlsx'))[0]
wb = openpyxl.load_workbook(f, read_only=True)
for ws in wb.worksheets:
    cur_c = None
    for row in ws.iter_rows(values_only=True):
        c = row[0]
        if c and clean(c) not in ('亚洲', '欧洲', '非洲', '美洲', '大洋洲', '北美洲', '南美洲',
                                   '国家（地区）', '已准入水生动物国家和地区及品种名单', ''):
            if not clean(c).isdigit() and len(clean(c)) <= 14:
                cur_c = clean(c)
        # 第2列种类, 第3列学名/中文
        if cur_c:
            for idx in (1, 2, 3):
                if len(row) > idx and row[idx]:
                    v = clean(row[idx])
                    if v and not v.isdigit() and len(v) <= 30 and v not in ('种类（分类至科）', '类别', '学名', '拉丁文', '中文'):
                        add(v, [cur_c])

# 5. 畜禽 xlsx: 动物品种, 国家
f = glob.glob(os.path.join(D, '_gacc_*畜禽品种*.xlsx'))[0]
wb = openpyxl.load_workbook(f, read_only=True)
ws = wb['Sheet2']
cur_p = None
for row in list(ws.iter_rows(values_only=True))[2:]:
    p, c = row[1], row[2]
    if p: cur_p = clean(p)
    if cur_p and c:
        add(cur_p, [clean(c)])

# 6. 咖啡 docx: 种类 -> 国家
f = glob.glob(os.path.join(D, '_gacc_*咖啡豆*可可豆*.docx'))[0]
d = docx.Document(f)
for row in d.tables[0].rows[1:]:
    cats = row.cells[0].text
    cs = row.cells[1].text
    for p in split_products(cats):
        add(p, split_countries(cs))

# 7. 粮食 docx: 种类 -> 国家
f = glob.glob(os.path.join(D, '_gacc_*粮食*.docx'))[0]
d = docx.Document(f)
for row in d.tables[0].rows[1:]:
    p = row.cells[1].text
    cs = row.cells[2].text
    add(clean(p), split_countries(cs))

# 8. 水果 docx: 国家 -> 水果种类
f = glob.glob(os.path.join(D, '_gacc_*新鲜水果*.docx'))[0]
d = docx.Document(f)
for row in d.tables[0].rows[1:]:
    c = row.cells[1].text
    ps = row.cells[2].text
    for p in split_products(ps):
        add(p, [clean(c)])

# 过滤: 去掉过泛/噪声
prod = {p: sorted(v) for p, v in prod_country.items() if len(v) >= 1 and 1 <= len(p) <= 20}
out = {'_note': '从 GACC 官方附件提取的产品->国家索引', 'n': len(prod), 'products': prod}
json.dump(out, open(os.path.join(D, '_products_index.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('products:', len(prod))
for probe in ['香蕉', '芒果', '葡萄', '蓝莓', '牛肉', '猪肉', '龙虾', '可可豆', '咖啡豆', '大豆', '玉米', '大麦', '奇亚籽', '三文鱼']:
    if probe in prod:
        print(f'  {probe}: {len(prod[probe])} 国 {prod[probe][:4]}')
    else:
        # 模糊
        hits = [p for p in prod if probe in p]
        print(f'  {probe}: 精确无, 含此字: {hits[:5]}')
