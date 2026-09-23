#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成检验科排班表清单（html/jyk_schedule/data/schedule.json）

流程：
    html/jyk_schedule/data/*.pdf  ──> generate_schedule_manifest.py ──> data/schedule.json ──> index.html 读取渲染

文件名约定：
    月度排班表：YYYY-MM-schedule.pdf        例：2026-09-schedule.pdf
    节假日排班表：YYYY-CODE-schedule.pdf    例：2026-ZQ-schedule.pdf（中秋节）

新增排班表只需把 PDF 放进 html/jyk_schedule/data/，再运行本脚本即可，
无需修改 index.html 里的任何代码。
"""

import io
import json
import os
import re
import sys
from datetime import datetime

# 设置 stdout/stderr 编码为 utf-8（Windows 控制台默认 GBK，会导致 emoji 报错）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ---------------- 配置 ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'html', 'jyk_schedule', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'schedule.json')

# 年份展示跨度（包含数据中出现的所有年份，另加最近 N 年）
YEAR_SPAN = 2

# 节假日定义：代码 -> (显示名, 排序用月份, 其他可识别别名)
HOLIDAYS = {
    'YD': ('元旦节', 1, ['YUAN', 'YUANDAN', 'XNY', 'XINNIAN', 'NEWYEAR']),
    'CJ': ('春节', 2, ['CHUNJIE', 'SJ', 'SPRING']),
    'QM': ('清明节', 4, ['QINGMING']),
    'LD': ('劳动节', 5, ['WY', 'WUYI', 'LAODONG', 'MAYDAY', '五一']),
    'DW': ('端午节', 6, ['DWF', 'DUANWU']),
    'ZQ': ('中秋节', 9, ['ZX', 'ZHONGQIU', 'MIDDLEAUTUMN']),
    'GQ': ('国庆节', 10, ['GUOQING', 'NATIONAL']),
}

# 名称 -> 代码（含中文名，按长度倒序匹配，避免“中秋节”被“秋”误伤）
HOLIDAY_ALIASES = {}
for _code, (_label, _month, _aliases) in HOLIDAYS.items():
    HOLIDAY_ALIASES[_label] = _code
    for _alias in _aliases:
        HOLIDAY_ALIASES[_alias] = _code

# PDF 文件名解析：2026-09-schedule.pdf / 2026-ZQ-schedule.pdf / 2026-国庆节.pdf / 2026年9月.pdf
RE_YEAR = re.compile(r'^(\d{4})$')
RE_MONTH = re.compile(r'^(\d{1,2})月?$')
RE_MONTH_CN = re.compile(r'^(\d{4})年(\d{1,2})月$')


def log(msg):
    sys.stdout.write(msg + '\n')


def warn(msg):
    sys.stderr.write(msg + '\n')


def normalize(token):
    """统一大小写并去掉常见分隔符，便于别名匹配。"""
    return re.sub(r'[\s\-_（）()第期]', '', token).upper()


# 名称 -> 代码（键已归一化，含中文名、代码本身及别名，避免“中秋节”被“秋”误伤）
HOLIDAY_ALIASES = {}
for _code, (_label, _month, _aliases) in HOLIDAYS.items():
    for _alias in [_code, _label] + list(_aliases):
        HOLIDAY_ALIASES[normalize(_alias)] = _code

# 供“名称与其它词粘连”的场景使用，如“2026-中秋节值班表”
HOLIDAY_SUBSTRINGS = sorted(HOLIDAY_ALIASES.keys(), key=len, reverse=True)


def parse_filename(filename):
    """
    解析 PDF 文件名，返回 (year, kind, value, code)：
        kind = 'month'   -> value 为 1-12
        kind = 'holiday' -> value 为排序月份，code 为节假日代码
    解析失败返回 None。
    """
    stem = os.path.splitext(filename)[0]

    # 形如 2026年9月
    m = RE_MONTH_CN.match(stem)
    if m:
        return int(m.group(1)), 'month', int(m.group(2)), None

    # 去掉无意义的后缀（-schedule / -排班表 / -值班表 等）
    tokens = [t for t in re.split(r'[-_]', stem) if t]
    tokens = [t for t in tokens if normalize(t) not in ('SCHEDULE', 'PAIBANBIAO', '排班表', '值班表', '排班')]
    if not tokens:
        return None

    # 年份：第一段必须是 4 位数字
    if not RE_YEAR.match(tokens[0]):
        return None
    year = int(tokens[0])
    tokens = tokens[1:]

    month = None
    code = None
    for token in tokens:
        key = normalize(token)
        if RE_MONTH.match(token):
            n = int(RE_MONTH.match(token).group(1))
            if 1 <= n <= 12:
                month = n
                continue
        # 节假日：先整段匹配代码/别名，再匹配名称与其它词粘连的情况（如“中秋节值班表”）
        if key in HOLIDAY_ALIASES:
            code = HOLIDAY_ALIASES[key]
            month = HOLIDAYS[code][1]
            continue
        for alias in HOLIDAY_SUBSTRINGS:
            if len(alias) > 1 and alias in key:
                code = HOLIDAY_ALIASES[alias]
                month = HOLIDAYS[code][1]
                break
        if code:
            continue

    if code:
        return year, 'holiday', month, code
    if month:
        return year, 'month', month, None
    return None


def scan_files():
    """扫描数据目录，返回 {year: {(kind, value): filename}} 及解析失败的列表。"""
    found = {}
    unparsed = []

    if not os.path.isdir(DATA_DIR):
        warn('✖ 目录不存在：%s' % DATA_DIR)
        return found, unparsed

    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.lower().endswith('.pdf'):
            continue
        parsed = parse_filename(filename)
        if not parsed:
            unparsed.append(filename)
            continue
        year, kind, value, code = parsed
        key = (kind, value if kind == 'month' else code)
        bucket = found.setdefault(year, {})
        if key in bucket:
            warn('⚠ 同类排班表重复，已忽略：%s（保留 %s）' % (filename, bucket[key]))
            continue
        bucket[key] = filename

    return found, unparsed


def build_manifest(found):
    """按年份展开全部选项（12 个月 + 7 个节假日），缺失的标记 available=False。"""
    now = datetime.now()
    years = set(found.keys())
    for offset in range(YEAR_SPAN):
        years.add(now.year - offset)

    manifest_years = []
    for year in sorted(years, reverse=True):
        bucket = found.get(year, {})
        entries = []

        for month in range(1, 13):
            filename = bucket.get(('month', month))
            entries.append({
                'id': '%d-%02d' % (year, month),
                'kind': 'month',
                'month': month,
                'label': '%d月' % month,
                'file': 'data/%s' % (filename or '%d-%02d-schedule.pdf' % (year, month)),
                'available': bool(filename),
            })

        for code in HOLIDAYS:
            label, month, _aliases = HOLIDAYS[code]
            filename = bucket.get(('holiday', code))
            entries.append({
                'id': '%d-%s' % (year, code),
                'kind': 'holiday',
                'code': code,
                'month': month,
                'label': label,
                'file': 'data/%s' % (filename or '%d-%s-schedule.pdf' % (year, code)),
                'available': bool(filename),
            })

        # 排序：按日期（节假日所在月份），同月月度在前、节假日在后
        entries.sort(key=lambda e: (e['month'], 1 if e['kind'] == 'holiday' else 0))
        manifest_years.append({'year': year, 'entries': entries})

    available_count = sum(1 for y in manifest_years for e in y['entries'] if e['available'])

    return {
        'generatedAt': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'holidays': {code: {'label': HOLIDAYS[code][0], 'month': HOLIDAYS[code][1]} for code in HOLIDAYS},
        'years': manifest_years,
    }, available_count


def write_if_changed(path, data):
    """内容不变则不写文件（忽略 generatedAt，保证幂等，避免无意义的 git diff）。"""
    def comparable(obj):
        return {k: v for k, v in obj.items() if k != 'generatedAt'}

    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    old = None
    if os.path.exists(path):
        with io.open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        try:
            old = comparable(json.loads(raw))
        except ValueError:
            old = None
    if old is not None and old == comparable(data):
        return False
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return True


def main():
    log('📖 正在扫描排班表目录...')
    log('   %s' % DATA_DIR)

    found, unparsed = scan_files()
    manifest, available_count = build_manifest(found)

    if unparsed:
        warn('')
        warn('⚠ 以下文件无法识别命名规则，未加入清单：')
        for filename in unparsed:
            warn('   • %s' % filename)
        warn('   命名约定：月度 YYYY-MM-schedule.pdf；节假日 YYYY-CODE-schedule.pdf（CODE 见 HOLIDAYS）')

    changed = write_if_changed(OUTPUT_FILE, manifest)

    log('')
    log('📅 年份：%s' % '、'.join(str(y['year']) for y in manifest['years']))
    for year_info in manifest['years']:
        have = [e for e in year_info['entries'] if e['available']]
        missing = [e['label'] for e in year_info['entries'] if not e['available']]
        log('   • %d年：已有 %d 项（%s）%s' % (
            year_info['year'],
            len(have),
            '、'.join(e['label'] for e in have) or '无',
            ('，缺失 %d 项' % len(missing)) if missing else '',
        ))
    log('')
    if changed:
        log('✅ 已生成：%s' % os.path.relpath(OUTPUT_FILE, BASE_DIR))
    else:
        log('✅ 清单无变化：%s' % os.path.relpath(OUTPUT_FILE, BASE_DIR))
    log('💡 提示：新增 PDF 后重新运行本脚本即可更新清单，无需改动页面代码')
    return 0


if __name__ == '__main__':
    sys.exit(main())
