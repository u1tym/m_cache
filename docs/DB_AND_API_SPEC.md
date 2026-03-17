# DBレイアウト・API仕様書（生成AI向け）

このドキュメントは、データベーススキーマとREST APIの仕様を一意に定義するものです。他の生成AIが実装や検証を行う際の参照として利用してください。

- **RDBMS**: PostgreSQL
- **日付・時刻フォーマット**: 日付は ISO 8601 の日のみ（例: `2025-03-17`）。APIのJSONでは文字列でやり取りする。
- **文字列**: すべて `character varying`（VARCHAR）として扱う。

---

## 1. データベーススキーマ

### 1.1 テーブル一覧

| スキーマ | テーブル名 | 説明 |
|----------|------------|------|
| public | payment_sources | 支払元マスタ（クレジットカード等） |
| public | transactions | 収支（取引） |

### 1.2 テーブル: public.payment_sources

支払元を表すマスタ。締日・支払日ルールを持つ。

| 列名 | 型 | NULL | デフォルト | 説明 |
|------|-----|------|------------|------|
| id | integer | NOT NULL | nextval('payment_sources_id_seq'::regclass) | 主キー |
| name | character varying | NOT NULL | - | 名称 |
| closing_day | integer | NOT NULL | - | 締日（1〜31、0の場合は「締日なし」） |
| pay_month_diff | integer | NOT NULL | - | 支払月差分（締め月から何ヶ月後に支払うか） |
| pay_day | integer | NOT NULL | - | 支払日（1〜31） |

- **主キー**: `payment_sources_pkey` (id)
- **インデックス**: `ix_payment_sources_id` btree (id)
- **参照元**: transactions.payment_source_id がこの id を参照する。

### 1.3 テーブル: public.transactions

1件の収支（支出）取引を表す。

| 列名 | 型 | NULL | デフォルト | 説明 |
|------|-----|------|------------|------|
| id | integer | NOT NULL | nextval('transactions_id_seq'::regclass) | 主キー |
| used_date | date | NOT NULL | - | 利用日 |
| purpose | character varying | NOT NULL | - | 目的 |
| memo | character varying | NOT NULL | - | メモ |
| amount | integer | NOT NULL | - | 金額（整数、単位はアプリで解釈） |
| payment_source_id | integer | NOT NULL | - | 支出元ID（payment_sources.id への外部キー） |
| paid_date | date | NOT NULL | - | 支出日（実際の支払日） |
| budget_name | character varying | NOT NULL | - | 予算名 |
| created_at | timestamp without time zone | NOT NULL | now() | 作成日時 |
| updated_at | timestamp without time zone | NOT NULL | now() | 更新日時 |

- **主キー**: `transactions_pkey` (id)
- **インデックス**: `ix_transactions_id` btree (id)
- **外部キー**: `transactions_payment_source_id_fkey` — payment_source_id REFERENCES payment_sources(id)

---

## 2. API 仕様

ベースURLは未定義（デプロイ環境に依存）。パスは先頭のスラッシュから記述する。

- **成功時**: 本文に記載のJSONを返す。特に断りがなければ HTTP 200。
- **エラー時**: 404 のときは `{"detail": "メッセージ"}` 形式のJSONを返す。

---

### API-1: 支出情報取得

- **メソッド・パス**: `GET /payment-sources`
- **概要**: 支払元の一覧（id と name のみ）を返す。
- **リクエスト**: パラメータなし。ボディなし。
- **レスポンス**: HTTP 200。JSON:

```json
{
  "items": [
    { "id": 1, "name": "カードA" },
    { "id": 2, "name": "カードB" }
  ]
}
```

- **型**: `items` は配列。各要素は `{ "id": integer, "name": string }`。
- **処理**: payment_sources を id の昇順で取得し、各レコードの id と name を返す。

---

### API-2: 支出情報登録

- **メソッド・パス**: `POST /payment-sources`
- **概要**: 支払元を1件登録する。
- **リクエスト**: Content-Type: application/json。ボディ:

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| name | string | ○ | 名称 |
| closing_day | integer | ○ | 締日 |
| pay_month_diff | integer | ○ | 支払月差分 |
| pay_day | integer | ○ | 支払日 |

- **レスポンス**: HTTP 200。登録された1件を返す:

```json
{
  "id": 1,
  "name": "カードA",
  "closing_day": 25,
  "pay_month_diff": 1,
  "pay_day": 10
}
```

- **処理**: 上記4項目を payment_sources に INSERT し、発番された id を含むレコードを返す。

---

### API-3: 支払日算出

- **メソッド・パス**: `POST /calc-paid-date`
- **概要**: 利用日と支払元IDから、その支払元のルールに基づく「支払日」を算出する。
- **リクエスト**: Content-Type: application/json。ボディ:

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| used_date | string (date) | ○ | 利用日（例: "2025-03-17"） |
| payment_source_id | integer | ○ | 支払元ID（payment_sources.id） |

- **レスポンス（成功）**: HTTP 200:

```json
{
  "paid_date": "2025-04-10"
}
```

- **レスポンス（エラー）**: 指定した payment_source_id が payment_sources に存在しない場合、HTTP 404。本文は `{"detail": "..."}` 形式。
- **処理**:
  1. payment_sources から id = payment_source_id のレコードを1件取得する。
  2. 存在しなければ 404 を返す。
  3. 存在する場合、そのレコードの closing_day, pay_month_diff, pay_day と、リクエストの used_date を使って支払日を算出する（下記アルゴリズム）。
  4. 算出した日付を paid_date として返す。

**支払日算出アルゴリズム**（引数: 利用日 used_date, 締日 closing_day, 支払月差分 pay_month_diff, 支払日 pay_day）:

- もし `closing_day == 0` なら、支払日 = used_date として返す。
- そうでない場合:
  - used_date の「日」を day、年を year、月を month とする。
  - もし `day <= closing_day` なら、対象月 = month + pay_month_diff。
  - もし `day > closing_day` なら、対象月 = month + pay_month_diff + 1。
  - 対象月が 12 を超える場合は 12 を引き、年を 1 増やす。1 未満の場合は 12 を足し、年を 1 減らす。これを繰り返して 1〜12 に正規化する。
  - 支払日の「日」は、pay_day と「対象年・対象月の月末日」の小さい方とする（例: pay_day=31 で対象月が2月なら 28 or 29）。
  - 支払日 = (対象年, 対象月, 上記で決めた日) の日付を返す。

---

### API-4: 収支登録

- **メソッド・パス**: `POST /transactions`
- **概要**: 収支（取引）を1件登録する。
- **リクエスト**: Content-Type: application/json。ボディ:

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| used_date | string (date) | ○ | 利用日 |
| purpose | string | ○ | 目的 |
| memo | string | - | メモ（省略時は空文字） |
| amount | integer | ○ | 金額 |
| payment_source_id | integer | ○ | 支出元ID（payment_sources.id） |
| paid_date | string (date) | ○ | 支出日 |
| budget_name | string | - | 予算名（省略または空文字の場合は「未分類」にする） |

- **レスポンス**: HTTP 200。登録された1件を返す（created_at, updated_at は含めなくてよい）:

```json
{
  "id": 1,
  "used_date": "2025-03-01",
  "purpose": "食費",
  "memo": "メモ",
  "amount": 3000,
  "payment_source_id": 1,
  "paid_date": "2025-03-01",
  "budget_name": "食費予算"
}
```

- **処理**: 上記項目を transactions に INSERT。budget_name が未指定または空文字のときは "未分類" を設定する。memo 未指定時は "" を設定する。

---

### API-5: 収支更新

- **メソッド・パス**: `PUT /transactions`
- **概要**: 既存の収支1件を、指定した項目だけ更新する。
- **リクエスト**: Content-Type: application/json。ボディ:

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| id | integer | ○ | 更新対象の transactions.id |
| used_date | string (date) | - | 利用日（指定時のみ更新） |
| purpose | string | - | 目的（指定時のみ更新） |
| memo | string | - | メモ（指定時のみ更新） |
| amount | integer | - | 金額（指定時のみ更新） |
| payment_source_id | integer | - | 支出元ID（指定時のみ更新） |
| paid_date | string (date) | - | 支出日（指定時のみ更新） |
| budget_name | string | - | 予算名（指定時のみ更新） |

- **レスポンス（成功）**: HTTP 200。例: `{"message": "updated"}`。
- **レスポンス（エラー）**: id に該当する transactions が存在しない場合、HTTP 404。本文は `{"detail": "..."}` 形式。
- **処理**: id で transactions を1件取得。存在しなければ 404。存在すれば、リクエストで指定されたキー（id 以外）のみ更新する。未指定のキーは既存値を維持する。

---

### API-6: 収支1件検索

- **メソッド・パス**: `GET /transactions/{transaction_id}`
- **概要**: 指定したIDの収支1件を、支出元名付きで返す。
- **リクエスト**: パスパラメータ `transaction_id`（integer）= transactions.id。
- **レスポンス（成功）**: HTTP 200:

```json
{
  "id": 1,
  "used_date": "2025-03-01",
  "purpose": "食費",
  "memo": "メモ",
  "amount": 3000,
  "payment_source_id": 1,
  "paid_date": "2025-03-01",
  "budget_name": "食費予算",
  "payment_source_name": "カードA"
}
```

- **レスポンス（エラー）**: 該当する transactions が存在しない場合、HTTP 404。
- **処理**: transactions を transaction_id で取得し、紐づく payment_sources の name を payment_source_name として含めて返す。

---

### API-7: 収支利用日期間リスト検索

- **メソッド・パス**: `POST /transactions/search-by-used-date`
- **概要**: 利用日が指定期間内の収支のリストを返す。
- **リクエスト**: Content-Type: application/json。ボディ:

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| date_from | string (date) | ○ | 期間の開始日（この日を含む） |
| date_to | string (date) | ○ | 期間の終了日（この日を含む） |

- **条件**: `date_from <= used_date <= date_to` のレコードを対象とする。
- **レスポンス**: HTTP 200:

```json
{
  "items": [
    {
      "id": 1,
      "used_date": "2025-03-15",
      "purpose": "食費",
      "amount": 3000,
      "payment_source_id": 1,
      "paid_date": "2025-04-10",
      "budget_name": "食費",
      "payment_source_name": "カードA"
    }
  ]
}
```

- **型**: 各要素に memo は含めない。payment_source_name は payment_sources.name。並び順は used_date, id の昇順でよい。

---

### API-8: 収支支払日期間リスト検索

- **メソッド・パス**: `POST /transactions/search-by-paid-date`
- **概要**: 支出日が指定期間内の収支のリストを返す。
- **リクエスト**: Content-Type: application/json。ボディ:

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| date_from | string (date) | ○ | 期間の開始日（この日を含む） |
| date_to | string (date) | ○ | 期間の終了日（この日を含む） |

- **条件**: `date_from <= paid_date <= date_to` のレコードを対象とする。
- **レスポンス**: HTTP 200。形式は API-7 と同じ（items の各要素は id, used_date, purpose, amount, payment_source_id, paid_date, budget_name, payment_source_name）。並び順は paid_date, id の昇順でよい。

---

## 3. 用語対応

| 日本語 | 英（DB/API） | 説明 |
|--------|----------------|------|
| 支出元 / 支払元 | payment_source | クレジットカード等の支払い元。payment_sources の1行。 |
| 収支 / 取引 | transaction | 1件の支出。transactions の1行。 |
| 利用日 | used_date | その取引をした日。 |
| 締日 | closing_day | 支払元の締め日（0=締日なし）。 |
| 支払月差分 | pay_month_diff | 締め月から何ヶ月後に支払うか。 |
| 支払日 | pay_day | 支払いが行われる日（月内の日付）。 |
| 支出日 | paid_date | 実際の支払日（transactions に保存する日付）。 |
| 予算名 | budget_name | 取引を分類するための名前。 |

---

## 4. エラー一覧

| HTTP | 発生条件 |
|------|-----------|
| 404 | API-3: payment_source_id が payment_sources に存在しない。 |
| 404 | API-5: 指定した id の transactions が存在しない。 |
| 404 | API-6: 指定した transaction_id の transactions が存在しない。 |

上記以外のバリデーションエラー（必須項目欠落など）は、実装に応じて 422 等を返す。
