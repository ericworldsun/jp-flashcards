# -*- coding: utf-8 -*-
"""從 Obsidian vault 的「單字表整理」筆記產生 data.js（單字卡資料）。

用法：python build_data.py
每次 vault 筆記更新後重跑一次，然後 git commit + push 即可更新 PWA。
"""
import os, re, json, hashlib

VAULT = r'C:\Users\ericw\OneDrive\Documents\obsidian\日文學習\單字表整理'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.js')

NOTES = [
    ('01 基礎單字總表.md', 'base',    '基礎單字'),
    ('02 影劇動畫生字.md', 'media',   '影劇動畫'),
    ('03 文法句型總表.md', 'grammar', '文法句型'),
    ('04 漢字音讀表.md',   'kanji',   '漢字音讀'),
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
            if deck in ('base', 'media'):
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

def main():
    decks = []
    total = 0
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
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('// 自動產生，勿手改。來源：Obsidian vault 單字表整理／build_data.py\n')
        f.write('const DECKS = ')
        f.write(json.dumps(decks, ensure_ascii=False, separators=(',', ':')))
        f.write(';\n')
    print('total %d cards -> %s' % (total, OUT))

if __name__ == '__main__':
    main()
