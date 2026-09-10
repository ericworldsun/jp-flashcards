# -*- coding: utf-8 -*-
"""從 Obsidian vault 的「單字表整理」筆記產生 data.js（單字卡資料）。

用法：python build_data.py [--force]
每次 vault 筆記更新後重跑一次，然後 git commit + push 即可更新 PWA。
防呆：某牌組張數比上次 data.js 少 20% 以上時中止（可能是筆記被誤刪/改格式），
確認無誤後加 --force 才覆寫。
"""
import os, re, sys, json, hashlib

VAULT = r'C:\Users\ericw\OneDrive\Documents\obsidian\日文學習\單字表整理'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.js')

NOTES = [
    ('01 基礎單字總表.md', 'base',    '基礎單字'),
    ('02 影劇動畫生字.md', 'media',   '影劇動畫'),
    ('03 文法句型總表.md', 'grammar', '文法句型'),
    ('04 漢字音讀表.md',   'kanji',   '漢字音讀'),
    ('05 小說生字.md',     'novel',   '小說生字'),
]

def parse_note(path, deck):
    cards = []
    section = ''
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            m = re.match(r'^##\s+(.+?)（', line)
            if m:
                section = m.group(1).strip()
                continue
            if not (line.startswith('|') and line.endswith('|')):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            if not cells or cells[0] in ('單字', '句型', '漢字') or set(cells[0]) <= {'-'}:
                continue
            if deck in ('base', 'media', 'novel'):
                if len(cells) < 4:
                    continue
                w, r, mn, src = cells[0], cells[1], cells[2], cells[3]
            elif deck == 'grammar':
                if len(cells) < 4:
                    continue
                kana, kanji, mn, src = cells[0], cells[1], cells[2], cells[3]
                w, r = (kanji if kanji else kana), kana
            else:  # kanji
                if len(cells) < 2:
                    continue
                w, r, mn, src = cells[0], cells[1], '', '漢字'
            if not w:
                continue
            cid = hashlib.md5((deck + '|' + w + '|' + r).encode('utf-8')).hexdigest()[:10]
            cards.append({'id': cid, 'w': w, 'r': r, 'm': mn, 's': src, 'sec': section})
    return cards

def load_prev_counts():
    """讀上一版 data.js 的各牌組張數（讀不到就回空 dict，不擋新建）。"""
    try:
        with open(OUT, encoding='utf-8') as f:
            txt = f.read()
        m = re.search(r'const DECKS = (\[.*\]);', txt, re.S)
        if not m:
            return {}
        return {d['key']: len(d['cards']) for d in json.loads(m.group(1))}
    except (OSError, ValueError, KeyError):
        return {}

def main():
    force = '--force' in sys.argv
    if not os.path.isdir(VAULT):
        sys.exit('錯誤：vault 路徑不存在：%s\n（OneDrive 沒同步？路徑改了？）' % VAULT)
    prev = load_prev_counts()
    decks = []
    total = 0
    warnings = []
    for fname, key, label in NOTES:
        cards = parse_note(os.path.join(VAULT, fname), key)
        # 去掉同 deck 內重複 id（保險）
        seen = set()
        uniq = []
        for c in cards:
            if c['id'] in seen:
                continue
            seen.add(c['id'])
            uniq.append(c)
        decks.append({'key': key, 'label': label, 'cards': uniq})
        total += len(uniq)
        print('%s: %d cards' % (label, len(uniq)))
        if key in prev and prev[key] > 0 and len(uniq) < prev[key] * 0.8:
            warnings.append('警告：牌組「%s」從 %d 張掉到 %d 張（-%.0f%%）'
                            % (label, prev[key], len(uniq), (1 - len(uniq) / prev[key]) * 100))
    if warnings and not force:
        print('\n'.join(warnings))
        sys.exit('張數驟減，疑似筆記被誤刪或格式跑掉；確認無誤請加 --force 重跑。data.js 未覆寫。')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('// 自動產生，勿手改。來源：Obsidian vault 單字表整理／build_data.py\n')
        f.write('const DECKS = ')
        f.write(json.dumps(decks, ensure_ascii=False, separators=(',', ':')))
        f.write(';\n')
    print('total %d cards -> %s' % (total, OUT))

if __name__ == '__main__':
    main()
