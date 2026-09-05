# 海外向けホームページ初版の進め方

このプロトタイプは「英語1ページ + イベント一覧 + 申請リンク集」を最小単位にしています。まずはこの形で公開し、運用しながら CMS 化や多言語追加に進むのが現実的です。

## 1. 公開前に決めること

- 申請導線: LINE、Google Form、Tally、Typeform、PokerGuild など、どこで予約・申請を受けるか決める。
- イベント情報の責任者: 開始時間、レイトレジスト、参加費、リエントリー、賞典表現を誰が更新確認するか決める。
- 法務表現: "casino"、"bet"、"cash prize"、"cash-out" などの英語表現は避け、アミューズメントポーカーであることを明記する。
- 多言語範囲: 最初は English / Japanese。次に繁体中文、簡体中文、韓国語の順で増やすと運用しやすい。

## 2. 更新するファイル

- `events.json`: PokerGuildから取得した直近トーナメント一覧と、日中・深夜のアミューズメントキャッシュゲーム表。ここを変更するとページのゲーム欄が変わります。
- `app.js`: 多言語テキスト。サイト全体の文言を増やす場合に編集します。
- `assets/official-mainvisual.png`: ヒーロー背景と写真レーンで使う横長の店舗写真です。
- `assets/official-mainvisual-sp.png`: スマホ向けヒーロー背景と写真レーンで使う店舗写真です。

イベント1件の基本項目:

```json
{
  "id": "unique-event-id",
  "category": "tournament",
  "date": "2026-09-05",
  "start": "17:10",
  "late": "20:20",
  "title": { "en": "Event title", "ja": "イベント名" },
  "description": { "en": "Short summary", "ja": "短い説明" },
  "entry": "5,000 JPY",
  "reEntry": "5,000 JPY",
  "addon": "2,000 JPY",
  "game": "No Limit Texas Hold'em",
  "stack": "15,000",
  "link": "https://..."
}
```

## 3. トーナメントの自動更新

公開ページのトーナメント情報は、GitHub ActionsがPokerGuildから自動取得します。

- 自動更新: 日本時間の 00:00 / 06:00 / 12:00 / 18:00
- 取得範囲: 実行日から直近14日分
- 取得元: `https://pokerguild.jp/room?ik=4&tb=1`
- 取得内容: 開始時間、レイトレジスト、参加費、リエントリー、ゲーム種目、スタック、プライズ、順位別プライズ詳細
- 反映先: `outputs/site/events.json` と `docs/events.json`
- リングゲーム: 現在稼働卓は取得せず、日中・深夜の固定システムだけ表示

急ぎで更新する場合:

1. GitHubのリポジトリを開く
2. `Actions` を開く
3. `Update PokerGuild tournament data` を選ぶ
4. `Run workflow` を押す

GitHub Pagesへの反映は、通常は数十秒から数分程度かかります。

ローカルで確認する場合:

```sh
python3 outputs/site/tools/update-pokerguild-events.py --out outputs/site/events.json --days 14
```

その後、`outputs/site/events.json` を `docs/events.json` に反映して公開します。

## 4. 次の制作ステップ

1. 実リンクを確定する  
   LINE、申請フォーム、公式スケジュール、SNS、Google Maps のリンクを最終版にします。

2. 店舗写真に差し替える  
   海外の方は「本当に行ける場所か」を写真で判断します。入口、店内、受付、テーブル、ビル外観があると強いです。

3. 英語原稿を店舗ルールに合わせる  
   年齢確認、支払い方法、初心者講習の実施条件、言語対応、服装、飲食、キャンセル条件を確認します。

4. イベント更新方式を決める  
   現在はPokerGuild自動取得です。取得が不安定になった場合は、Googleスプレッドシート管理やCMS化を検討します。

5. URL 設計を決める  
   本番では `/en/` `/ja/` `/zh/` `/ko/` のような言語別 URL にすると検索と共有がしやすいです。

6. 多言語レビューを入れる  
   自動翻訳で初稿を作り、料金・規約・注意事項だけ人間が確認する流れが安全です。

## 5. CMS 化するなら

おすすめは `microCMS + Next.js` か `WordPress` です。

- 更新担当者が非エンジニア中心: WordPress または STUDIO
- 表示速度や自由度を優先: Next.js + microCMS
- まず低コストに試す: 静的HTML + JSON更新

最初の CMS 項目は、`News`、`Events`、`FAQ`、`Application Links` の4つで十分です。
