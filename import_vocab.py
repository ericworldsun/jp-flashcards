# -*- coding: utf-8 -*-
"""把讀解講義匯出的生字本（讀解生字本_inbox*.json）合併進 inbox.json，然後跑 sync_inbox.py 整併。

來源尋找順序：命令列參數指定的路徑 → 本資料夾 → 使用者的 Downloads（取最新的一個）。
合併規則：與 inbox.json 既有項目以 (deck|單字|讀音) 去重；sync_inbox 本身還會再對 vault 去重，重跑安全。
匯入成功後，來源檔改名為 *.imported.json 避免下次重複吃到。
用法：python import_vocab.py [json路徑] [--no-sync]（--no-sync 只合併不整併，給測試用）
"""
import os, sys, json, glob, subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(HERE, 'inbox.json')
PATTERN = '讀解生字本_inbox*.json'
NO_SYNC = '--no-sync' in sys.argv

def find_source():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args:
        if os.path.isfile(args[0]):
            return args[0]
        sys.exit('找不到指定的檔案：' + args[0])
    cands = []
    for folder in (HERE, os.path.join(os.path.expanduser('~'), 'Downloads')):
        cands += [p for p in glob.glob(os.path.join(folder, PATTERN)) if not p.endswith('.imported.json')]
    if not cands:
        sys.exit('找不到 ' + PATTERN + '（請先在講義頁的生字本按「匯出單字卡」，下載後放進本資料夾或 Downloads）')
    return max(cands, key=os.path.getmtime)

def clean(v):
    return (v or '').strip().replace('|', '／').replace('\n', ' ')

def key(c):
    return (c.get('deck', 'base'), clean(c.get('w')), clean(c.get('r')))

def main():
    src = find_source()
    print('來源：', src)
    with open(src, encoding='utf-8-sig') as f:   # 頁面匯出檔帶 BOM，utf-8-sig 兩者通吃
        incoming = json.load(f)
    if not isinstance(incoming, list):
        sys.exit('格式不對：應為 JSON 陣列')
    try:
        with open(INBOX, encoding='utf-8-sig') as f:
            raw = json.load(f)
        inbox = (raw.get('cards') if isinstance(raw, dict) else raw) or []   # 契約：{"cards":[...]}
    except Exception:
        inbox = []
    have = {key(c) for c in inbox}
    added = skipped = bad = 0
    for c in incoming:
        w = clean(c.get('w'))
        if not w:
            bad += 1
            continue
        k = ('base' if c.get('deck') not in ('base', 'media') else c['deck'], w, clean(c.get('r')))
        if k in have:
            skipped += 1
            continue
        have.add(k)
        inbox.append({'deck': k[0], 'w': w, 'r': clean(c.get('r')), 'm': clean(c.get('m')), 's': clean(c.get('s')) or '讀解講義'})
        added += 1
    with open(INBOX, 'w', encoding='utf-8') as f:
        json.dump({'cards': inbox}, f, ensure_ascii=False, indent=1)
    print(f'合併完成：新增 {added} 筆、重複略過 {skipped} 筆、無效 {bad} 筆（inbox 現有 {len(inbox)} 筆待整併）')
    dst = src[:-5] + '.imported.json'
    try:
        if os.path.exists(dst):
            os.remove(dst)
        os.rename(src, dst)
        print('來源檔已改名：', os.path.basename(dst))
    except OSError as e:
        print('（來源檔改名失敗，不影響匯入：', e, '）')
    if NO_SYNC:
        print('--no-sync：跳過整併。之後執行「一鍵同步新單字.bat」即可。')
        return
    if added == 0 and skipped >= 0 and not inbox:
        print('沒有需要整併的項目。')
        return
    print('接著執行 sync_inbox.py 整併進 vault…')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'sync_inbox.py')], cwd=HERE)
    sys.exit(r.returncode)

if __name__ == '__main__':
    main()
