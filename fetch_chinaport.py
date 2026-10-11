# -*- coding: utf-8 -*-
"""从 chinaport 进境动植物及其产品境外企业检疫注册登记系统 API 全量拉数据
聚合: 国 -> 产品类型/产品种类(注册数), 产品种类 -> 国(注册数)
带断点保存, 每页间隔避免限流
"""
import requests, warnings, json, io, sys, os, time
from collections import OrderedDict
warnings.filterwarnings('ignore')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'D:\Projects\gacc_dashboard_site'
OUT = os.path.join(BASE, 'data', 'chinaport_raw.json')
PART = os.path.join(BASE, 'data', 'chinaport_part.json')
LIMIT = 500
U = 'http://scintl.chinaport.gov.cn/aprwebserver/publicity/list'
h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0',
     'Referer': 'http://scintl.chinaport.gov.cn/aprwebserver/pages/apr/public/html/companyList.html',
     'Content-Type': 'application/json'}
s = requests.Session()

def fetch_page(page):
    body = json.dumps({'page': page, 'limit': LIMIT})
    for attempt in range(3):
        try:
            r = s.post(U, headers=h, data=body, timeout=40, verify=False)
            j = r.json()
            return j.get('data', {})
        except Exception as e:
            print(f'  page {page} attempt {attempt+1} ERR {type(e).__name__} {str(e)[:80]}')
            time.sleep(5)
    return None

# 断点: 记录已完成的页
done = set()
if os.path.exists(PART):
    try:
        saved = json.load(open(PART, encoding='utf-8'))
        done = set(saved.get('pages', []))
        rows_all = saved.get('rows', [])
    except Exception:
        rows_all = []

first = True
while True:
    page = 1
    while page not in done and not first:
        page += 1
        if page > 2000:  # 安全上限
            break
    # 拉一页
    d = fetch_page(page)
    if d is None:
        print(f'page {page} 拉取失败, 保存断点')
        break
    rows = d.get('rows', [])
    total = d.get('total', 0)
    print(f'page {page}: {len(rows)} rows, total {total}')
    rows_all.extend(rows)
    done.add(page)
    # 每 5 页保存一次断点
    if len(done) % 5 == 0:
        json.dump({'pages': list(done), 'rows': rows_all}, open(PART, 'w', encoding='utf-8'))
    first = False
    # 判断是否完成
    need = total // LIMIT + (1 if total % LIMIT else 0)
    if len(done) >= need:
        break
    time.sleep(1.0)

json.dump({'total': total, 'pages': list(done), 'rows': rows_all}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('saved', OUT, 'pages:', len(done), 'rows:', len(rows_all))
