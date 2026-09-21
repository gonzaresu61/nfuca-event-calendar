# 大学生協東京ブロック セミナーカレンダー

開催日（青）と申込締切（オレンジ）を確認できる非公式カレンダーです。月表示・一覧表示、エリア選択、スマートフォンに対応しています。

## GitHub Pagesで公開

1. 新しい公開リポジトリ `nfuca-event-calendar` に、このフォルダーの中身をアップロードします。隠しフォルダー `.github` も含めてください。
2. GitHubの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。
3. **Actions → 毎週更新とカレンダー公開 → Run workflow** を実行します。
4. 正常終了後、Pagesに表示されたURLを共有できます。

追加のAPIキー、有料AIサービス、サーバー契約は不要です。公開リポジトリとGitHub標準の実行環境を想定しています。

## 毎週の更新

毎週 **日曜日 09:17（日本時間）** に、6カテゴリの一覧と記事本文を取得し、予定データを保存してサイトを再公開します。GitHubの混雑により実行時刻は遅れることがあります。手動更新も上記のRun workflowで実行できます。

一覧の掲載日を開催日として使うことはありません。掲載年は本文に年のない日付の年を補うために使用し、11〜12月公開の記事の1〜2月予定は翌年扱いにします。曜日との矛盾は要確認にします。日本時間で終了した予定は表示しません。開催中の複数日企画は残りの日を表示します。

同じ名称・同じ日程・同じエリアの複数記事は新しい記事を優先します。新記事に締切がなく、古い記事にある場合は元の締切を参照元リンク付きで残します。新しい締切が明記されていれば置き換えます。名称が変わる告知などを万能に判定する仕組みではありません。

PDFや画像だけに日程がある記事、複数企画の区別が不明な記事、本文構造が変わった記事は、日付を推測せず「日付確認要」に表示します。日付なしの案内は直近180日分を対象にします。「ふくしま」ツアーの3行程と、開催要項で置き換えられたSPK・秋の共済セミナーの合同案内は個別に対応しています。

最初にセミナー一覧と各カテゴリの先頭ページを取得し、保存済みの今後の予定の出典も再確認します。全過去ページを巡回する仕組みではないため、運用開始時点で各カテゴリの先頭ページから外れていた記事は取得できないことがあります。

通信障害・一覧構造変更がある場合は公開を止めて直前のサイトを維持します。最終確認から8日以上経過するとサイトに注意を表示します。GitHub Actionsで失敗を確認してください。公開リポジトリで60日間活動がない場合、GitHubが定期実行を停止することがあります。この構成は成功時に確認日時を毎週コミットしますが、長期間失敗していた場合はActionsから再有効化が必要です。

## 手元で確認

Python 3.9以上、Node.js 18以上が必要です。

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/update_events.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/calendar.test.mjs
python3 -m http.server 8765 --directory dist
```

ブラウザで `http://localhost:8765` を開きます。HTMLファイルを直接開く方式ではデータ取得ができないため、上記のプレビューを使用してください。

## 構成

- `dist/`：公開するカレンダー画面と日程データ
- `scripts/update_events.py`：取得・日程判定・重複整理
- `.github/workflows/update-and-deploy.yml`：日曜更新と公開
- `tests/`：日付・締切延長・複数日開催・日本時間の日付境界の検証

## 情報元

- [大学生協東京ブロック セミナーのお知らせ](https://www.nfuca-tokyo.jp/seminar.html)
- [GitHub Pagesの公開ワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHubの定期実行の仕様](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

本サイトは大学生協東京ブロックの公式サイトではありません。最新の開催可否・申込条件は各記事の公式案内をご確認ください。
