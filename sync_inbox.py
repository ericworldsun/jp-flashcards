# -*- coding: utf-8 -*-
"""把 PWA 新增的單字（inbox.json）整併進 Obsidian vault 筆記，再重建 data.js 並推上線。

流程：git pull → 讀 inbox.json → 依五十音插入 vault 筆記正確段落（更新段落計數）
      → build_data.py → 清空 inbox.json → git commit + push

用法：python sync_inbox.py [--no-git]（--no-git 給測試用：不 pull/commit/push）
環境變數 JPFC_VAULT 可覆寫 vault 路徑（測試用）。
冪等：同一筆重跑會被去重跳過，中途失敗直接重跑即可。
"""
import os, re, sys, json, hashlib, subprocess

# cp950 主控台印不出部分字元時以 ? 代替,不要讓整併炸掉
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get('JPFC_VAULT') or r'C:\Users\ericw\OneDrive\Documents\obsidian\日文學習\單字表整理'
INBOX = os.path.join(HERE, 'inbox.json')
NO_GIT = '--no-git' in sys.argv

DECK_FILE = {
    'base':  '01 基礎單字總表.md',
    'media': '02 影劇動畫生字.md',
    'novel': '05 小說生字.md',
}

GYO_ORDER = ['あ行', 'か行', 'さ行', 'た行', 'な行', 'は行', 'ま行', 'や行', 'ら行', 'わ行', 'その他']
GYO_CHARS = [
    ('あ行', 'ぁあぃいぅうぇえぉお'),
    ('か行', 'かがきぎくぐけげこごゕゖ'),
    ('さ行', 'さざしじすずせぜそぞ'),
    ('た行', 'ただちぢっつづてでとど'),
    ('な行', 'なにぬねの'),
    ('は行', 'はばぱひびぴふぶぷへべぺほぼぽ'),
    ('ま行', 'まみむめも'),
    ('や行', 'ゃやゅゆょよ'),
    ('ら行', 'らりるれろ'),
    ('わ行', 'ゎわゐゑをん'),
]

def kata_to_hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in (s or ''))

def sort_key(w, r):
    return kata_to_hira((r or w).replace(' ', '').replace('　', ''))

def gyo_of(key):
    ch = key[:1]
    for g, chars in GYO_CHARS:
        if ch in chars:
            return g
    return 'その他'

def clean(v):
    return (v or '').strip().replace('|', '／').replace('\n', ' ')

def row_cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

def is_data_row(line):
    s = line.strip()
    if not (s.startswith('|') and s.endswith('|')):
        return False
    cells = row_cells(s)
    return bool(cells) and cells[0] not in ('單字', '句型', '漢字') and not set(cells[0]) <= {'-'}

def find_sections(lines):
    """回傳 [(段名, header_idx)]，段名含「行」字尾或 その他。"""
    out = []
    for i, ln in enumerate(lines):
        m = re.match(r'^##\s+(.+?)（\d+）\s*$', ln.strip()) or re.match(r'^##\s+(\S+)\s*$', ln.strip())
        if m:
            out.append((m.group(1).strip(), i))
    return out

def section_bounds(lines, start):
    """start=header_idx，回傳 (start, end)：end 為下一個 ## 或檔尾。"""
    for j in range(start + 1, len(lines)):
        if lines[j].startswith('## '):
            return start, j
    return start, len(lines)

def ensure_section(lines, gyo):
    """找到（必要時建立）目標段落，回傳 header_idx。"""
    secs = find_sections(lines)
    for name, idx in secs:
        if name == gyo:
            return idx
    # 建新段：插在 GYO_ORDER 中它後面第一個已存在段落之前；都沒有就放檔尾
    order = GYO_ORDER.index(gyo) if gyo in GYO_ORDER else len(GYO_ORDER)
    insert_at = len(lines)
    for name, idx in secs:
        if name in GYO_ORDER and GYO_ORDER.index(name) > order:
            insert_at = idx
            break
    block = [f'## {gyo}（0）', '', '| 單字 | 讀音 | 意思 | 來源 |', '|---|---|---|---|', '']
    prefix = 0
    if insert_at == len(lines) and lines and lines[-1].strip():
        block = [''] + block
        prefix = 1
    lines[insert_at:insert_at] = block
    return insert_at + prefix

def insert_card(lines, card):
    """插入一筆；回傳 'added' | 'dup'。"""
    w, r, m, s = clean(card.get('w')), clean(card.get('r')), clean(card.get('m')), clean(card.get('s'))
    key = sort_key(w, r)
    gyo = gyo_of(key)
    hdr = ensure_section(lines, gyo)
    start, end = section_bounds(lines, hdr)
    rows = [(i, row_cells(lines[i])) for i in range(start + 1, end) if is_data_row(lines[i])]
    for _, cells in rows:
        if cells[0] == w and (cells[1] if len(cells) > 1 else '') == r:
            return 'dup'
    new_line = f'| {w} | {r} | {m} | {s} |'
    pos = None
    for i, cells in rows:
        k = sort_key(cells[0], cells[1] if len(cells) > 1 else '')
        if k > key:
            pos = i
            break
    if pos is None:
        if rows:
            pos = rows[-1][0] + 1
        else:  # 空段：放在分隔列後
            pos = start + 1
            for j in range(start + 1, end):
                if lines[j].strip().startswith('|') and set(row_cells(lines[j])[0]) <= {'-'}:
                    pos = j + 1
                    break
    lines[pos:pos] = [new_line]
    return 'added'

def refresh_counts(lines):
    """把所有「## X（n）」標題的計數改成該段實際資料列數。"""
    for name, idx in find_sections(lines):
        start, end = section_bounds(lines, idx)
        n = sum(1 for j in range(start + 1, end) if is_data_row(lines[j]))
        if re.match(r'^##\s+.+?（\d+）\s*$', lines[idx].strip()):
            lines[idx] = re.sub(r'（\d+）', f'（{n}）', lines[idx], count=1)

def run(cmd, **kw):
    print('>', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=HERE, **kw)
    if r.returncode != 0:
        sys.exit(f'指令失敗：{" ".join(cmd)}')

def main():
    if not NO_GIT:
        run(['git', 'pull', '--ff-only'])

    with open(INBOX, encoding='utf-8') as f:
        cards = (json.load(f).get('cards')) or []
    if not cards:
        print('inbox.json 是空的，沒有待整併的單字。')
        return

    # 去重：已在 data.js（＝已整併過）的直接略過
    built_ids = set()
    data_path = os.path.join(HERE, 'data.js')
    if os.path.exists(data_path):
        with open(data_path, encoding='utf-8') as f:
            built_ids = set(re.findall(r'"id":\s*"([0-9a-f]{10})"', f.read()))

    added, skipped = [], []
    by_file = {}
    for c in cards:
        cid = c.get('id') or hashlib.md5((c.get('deck', '') + '|' + clean(c.get('w')) + '|' + clean(c.get('r'))).encode('utf-8')).hexdigest()[:10]
        if cid in built_ids:
            skipped.append((c, '已在 data.js'))
            continue
        fname = DECK_FILE.get(c.get('deck'))
        if not fname:
            skipped.append((c, f'不支援的牌組 {c.get("deck")}'))
            continue
        by_file.setdefault(fname, []).append(c)

    for fname, cs in by_file.items():
        path = os.path.join(VAULT, fname)
        with open(path, 'rb') as f:
            raw = f.read()
        eol = '\r\n' if b'\r\n' in raw else '\n'
        text = raw.decode('utf-8-sig') if raw.startswith(b'\xef\xbb\xbf') else raw.decode('utf-8')
        bom = raw.startswith(b'\xef\xbb\xbf')
        lines = text.split('\r\n' if eol == '\r\n' else '\n')
        for c in cs:
            res = insert_card(lines, c)
            if res == 'added':
                added.append((c, fname))
            else:
                skipped.append((c, '筆記已有同字'))
        refresh_counts(lines)
        out = eol.join(lines)
        with open(path, 'wb') as f:
            f.write((('\ufeff' if bom else '') + out).encode('utf-8'))
        print(f'✔ {fname}：寫入 {sum(1 for a in added if a[1] == fname)} 筆')

    print(f'整併完成：新增 {len(added)} 筆，跳過 {len(skipped)} 筆')
    for c, why in skipped:
        print(f'  跳過 {c.get("w")}：{why}')

    # 只要有處理過卡就重建：涵蓋「上次寫進 vault 後、重建前中斷」的情況
    run([sys.executable, os.path.join(HERE, 'build_data.py')])

    with open(INBOX, 'w', encoding='utf-8') as f:
        f.write('{"cards": []}\n')

    if not NO_GIT:
        run(['git', 'add', 'data.js', 'inbox.json'])
        r = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=HERE)
        if r.returncode != 0:
            run(['git', 'commit', '-m', f'PWA 新增單字整併 {len(added)} 筆'])
            run(['git', 'push'])
        else:
            print('沒有需要 commit 的變更。')
    print('全部完成 ✅')

if __name__ == '__main__':
    main()
