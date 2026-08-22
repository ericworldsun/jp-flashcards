# 日文單字卡 PWA

三面式日文單字卡：**漢字面・讀音面・語意面**一起複習，不是傳統兩面卡。
資料來自 Obsidian vault「單字表整理」（2021–2025 舊 Word 單字表去重彙整，3,415 張）。

- 線上網址：https://ericworldsun.github.io/jp-flashcards/
- 平板安裝：Chrome 開網址 → 選單 →「加到主畫面」→ 之後離線也能用

## 功能

- **三面卡**：每張卡有漢字／讀音／語意三面，先亮一面，點卡片依序翻開其餘兩面
- **起始面**可設定：輪流（預設，三面輪著考）／隨機／固定某一面
- **排程複習**：簡化版記憶曲線（忘記→今天重來；有點難/記得→間隔 1→3→7→16→35→80→180→365 天），每日新卡上限可調（預設 20）
- **自由刷**：不記進度隨機翻
- **牌組**：基礎單字 2625／影劇動畫 373／文法句型 376／漢字音讀 41，可複選
- **＋新增單字**：App 內直接加新字（基礎／影劇兩牌組），立刻可複習；透過 GitHub 同步回 Obsidian 筆記（見下）
- 進度存在瀏覽器 localStorage，設定裡可匯出／匯入 JSON 備份

## 檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 整個 App（單檔，無外部依賴） |
| `data.js` | 卡片資料（由 `build_data.py` 自動產生，勿手改） |
| `build_data.py` | 從 vault 的「單字表整理」筆記重新產生 data.js |
| `inbox.json` | 雲端收件匣：PWA 新增的單字暫存區（整併後自動清空） |
| `sync_inbox.py` / `一鍵同步新單字.bat` | 把 inbox 整併進 vault 筆記＋重建 data.js＋push |
| `sw.js` | Service worker（網路優先、離線退回快取） |
| `manifest.webmanifest` / `icon-*.png` | PWA 安裝資訊 |

## 更新資料流程

vault 筆記（`Obsidian\日文學習\單字表整理\`）改完後：

```
python build_data.py
git add -A && git commit -m "update data" && git push
```

推上去約一分鐘後 Pages 生效；App 開啟時網路優先會自動抓到新版。

## 新增單字 → 同步回 Obsidian

資料流：**PWA「＋」表單 → 雲端 inbox.json → 電腦一鍵整併 → vault 筆記＋data.js**

1. 手機/平板在 App 按「＋」新增（單字必填；純假名字讀音可留空）→ 卡片**立刻**進複習佇列（標「✍ 新增待整併」）
2. 有設 Token 就自動上傳到 repo 的 `inbox.json`；沒 Token 先存本機，之後可補上傳
3. 電腦雙擊 `一鍵同步新單字.bat`：pull → 依五十音把字插進 vault 筆記正確段落（含更新段落計數、去重）→ 重建 data.js → push
4. 整併前後卡片 id 不變（同一套雜湊），複習進度無縫延續

**Token 設定（每台裝置一次）**：GitHub → Settings → Developer settings → Fine-grained tokens
→ 只勾 `jp-flashcards` repo、權限只給 Contents: Read and write → 產生後貼到 App 設定「雲端同步」欄。

## 注意

- 卡片 id 由「牌組+單字+讀音」雜湊而成：筆記裡改意思不影響進度；改單字或讀音會被視為新卡。
- 進度只存在各裝置瀏覽器內（平板與電腦各自獨立），換裝置用匯出／匯入搬。
