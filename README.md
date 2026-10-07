# repo-config

danything と 5ym の**全リポジトリの git の運用の共通設定**(2026-10-07 に 5ym/renovate から改名)。

| 中身 | 在処 |
| --- | --- |
| 共有の Renovate プリセット | [default.json](default.json)(下の「使い方」) |
| GitHub 側で Renovate を回す | [.github/workflows/renovate.yml](.github/workflows/renovate.yml)(GitHub App doa-renovate) |
| リポジトリの設定を揃える | [repo-settings.json](repo-settings.json) を [.github/workflows/repo-settings.yml](.github/workflows/repo-settings.yml) が毎日と変更時に全リポジトリへ当てる(GitHub App doa-repo-settings。Administration の書き込みだけ) |

### リポジトリの設定

ブランチの更新の提案・自動マージ・マージ後のブランチ削除をオン、マージは squash だけ。新しいリポジトリも次の実行で揃い、
手で変えても戻る。変えたいときは repo-settings.json を直す(項目は GitHub の `PATCH /repos/{owner}/{repo}` の名前)。
Renovate の自動マージ(`platformAutomerge`)は、リポジトリで自動マージが許可されていないと十分に働かない。

## 使い方

各リポジトリの `renovate.json`:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>5ym/repo-config"]
}
```

## 設定内容

| まとまり | 自動マージ | ラベル | 中身 |
| --- | --- | --- | --- |
| `all dependencies` | する | | メジャー以外の全部。小さくて頻繁で、タグを戻せば済む |
| `major dependencies` | **しない** | `needs-review` | メジャー。とくにデータベースはタグを差し替えるだけでは上がらない(PostgreSQL は別メジャーが書いたデータディレクトリでは起動を拒否する) |
| `helm charts` | **しない** | `needs-review` | Helm の chart。更新の種類を問わない |

### `needs-review` ラベル

各リポジトリの Claude レビュー(`.github/workflows/claude-code-review.yml`)は既定で bot の PR を
飛ばす。**自分でマージされる PR をレビューしても誰も読まないから**で、それは正しい。
一方、人を待つ PR はレビューする価値がある。そこで自動マージしないまとまりにだけ
このラベルを付けて、workflow 側で

```yaml
!endsWith(github.event.pull_request.user.login, '[bot]') ||
contains(github.event.pull_request.labels.*.name, 'needs-review')
```

と拾えるようにしてある。

ほかに `reviewers: ["5ym"]` で PR のレビュワーを指定します。**自動マージする PR にも付ける**
(`assignAutomerge: true`。Renovate の既定では自動マージの PR にはレビュワーが付かない)。

### TypeScript は 7 未満

svelte-check が TypeScript 6 と 7 を並べて要る(7 は `@typescript/native` の別名で読む)ので、`typescript` を 7 に
上げると `bun run check` が起動しなくなる。7 つのリポジトリで同じ規則を書いていたのをここにまとめた。
もっと厳しく止めたいリポジトリ(denpa の `<6`)は自分の規則を持つ(後から読まれるほうが勝つ)。

### バージョン範囲は `bump`

`rangeStrategy: "bump"` で、範囲内の更新でも `package.json` の指定ごと上げる(`^5.39.8` → `^5.57.1`)。
既定のようにロックファイルだけを書き換える更新は **`bun.lock` では Renovate が行えず**、
範囲内のセキュリティ修正の PR が適用されないまま閉じられていた(danything/blog #38〜#40)。

`peerDependencies` だけは `widen`(`^5.0.0` → `^5.0.0 || ^6.0.0`)。ライブラリが対応範囲として
公開している値なので、最新に引き上げると利用者全員に更新を強いることになる。

### なぜ chart は種類を問わず外すのか

**chart の版は中身の大きさを表しません。** erpnext は `8.0.15` → `8.0.78` という「パッチ」で
キャッシュとキューを Dragonfly から Valkey に入れ替え、values に書いてあったメモリ上限を
丸ごと無効にしました(danything/gitops#25)。メジャーを分けるだけでは止まりません。

グループを分けてあるのは、chart を止めることで `all dependencies` の PR まで
自動マージされなくなるのを避けるためです。

`platformAutomerge` を使うため、対象リポジトリ側で **Settings → General → Allow auto-merge** を有効にしておく必要があります。

## Renovate を回す(self-hosted)

GitHub の `danything` と `5ym` は [.github/workflows/renovate.yml](.github/workflows/renovate.yml) が毎時 17 分に回す(Mend のクラウド版の App の代わり)。Forgejo(fj.doany.io)側は `doa/renovate` が回す。

- GitHub App [doa-renovate](https://github.com/apps/doa-renovate)(持ち主は danything)を danything と 5ym に入れてある
- 変数 `RENOVATE_APP_CLIENT_ID` / `RENOVATE_GIT_AUTHOR`、シークレット `RENOVATE_APP_PRIVATE_KEY`
- `renovate.json` の無いリポジトリには、上の `renovate.json` を足す onboarding の PR が出る。マージするまでそのリポジトリでは依存の PR は出ない(要らなければ PR を閉じれば以後出ない)
