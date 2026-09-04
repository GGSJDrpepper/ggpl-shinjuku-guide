# 海外向けホームページ初版の進め方

このプロトタイプは「英語1ページ + イベント一覧 + 申請リンク集」を最小単位にしています。まずはこの形で公開し、運用しながら CMS 化や多言語追加に進むのが現実的です。

## 1. 公開前に決めること

- 申請導線: LINE、Google Form、Tally、Typeform、PokerGuild など、どこで予約・申請を受けるか決める。
- イベント情報の責任者: 開始時間、レイトレジスト、参加費、リエントリー、賞典表現を誰が更新確認するか決める。
- 法務表現: "casino"、"bet"、"cash prize"、"cash-out" などの英語表現は避け、アミューズメントポーカーであることを明記する。
- 多言語範囲: 最初は English / Japanese。次に繁体中文、簡体中文、韓国語の順で増やすと運用しやすい。

## 2. 更新するファイル

- `events.json`: 曜日別のトーナメント一覧と、日中・深夜のアミューズメントキャッシュゲーム表。ここを変更するとページのゲーム欄が変わります。
- `app.js`: 多言語テキスト。サイト全体の文言を増やす場合に編集します。
- `assets/official-mainvisual.png`: ヒーロー背景と写真レーンで使う横長の店舗写真です。
- `assets/official-mainvisual-sp.png`: スマホ向けヒーロー背景と写真レーンで使う店舗写真です。
- `assets/hero-poker-room.png`: 写真レーンで使う店舗写真です。
- `assets/store-wide-hero.jpeg`: 写真レーンで使う店舗写真です。

イベント1件の基本項目:

```json
{
  "id": "unique-event-id",
  "category": "tournament",
  "weekday": "monday",
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

PokerGuildの掲載内容を参考に手動更新する場合:

```sh
python3 outputs/site/tools/update-pokerguild-events.py
```

このスクリプトは `https://pokerguild.jp/room?ik=4&tb=1` を読み込み、GoodGame Poker Live SHINJUKUの今日以降のトーナメントを `events.json` に出力します。現在の公開ページは、受付用iPadで安定して使えるように、PokerGuildを毎回直接読まず、確認済みの曜日別固定データを表示する仕様です。

スクリプトを実行した場合は、曜日別に整理し直してから公開してください。あわせて `app.js` 内の予備データも同じ内容にすると、HTMLを直接開いた場合も同じ表示になります。

## 3. 次の制作ステップ

1. 実リンクを確定する  
   LINE、申請フォーム、公式スケジュール、SNS、Google Maps のリンクを最終版にします。

2. 店舗写真に差し替える  
   海外の方は「本当に行ける場所か」を写真で判断します。入口、店内、受付、テーブル、ビル外観があると強いです。

3. 英語原稿を店舗ルールに合わせる  
   年齢確認、支払い方法、初心者講習の実施条件、言語対応、服装、飲食、キャンセル条件を確認します。

4. イベント更新方式を決める  
   基本は曜日別の固定JSON更新で十分です。毎週内容が大きく変わる運用になった場合だけ、CMSや予約システム連携を検討します。

5. URL 設計を決める  
   本番では `/en/` `/ja/` `/zh/` `/ko/` のような言語別 URL にすると検索と共有がしやすいです。

6. 多言語レビューを入れる  
   自動翻訳で初稿を作り、料金・規約・注意事項だけ人間が確認する流れが安全です。

## 4. CMS 化するなら

おすすめは `microCMS + Next.js` か `WordPress` です。

- 更新担当者が非エンジニア中心: WordPress または STUDIO
- 表示速度や自由度を優先: Next.js + microCMS
- まず低コストに試す: 静的HTML + JSON更新

最初の CMS 項目は、`News`、`Events`、`FAQ`、`Application Links` の4つで十分です。
