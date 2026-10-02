# renovate

共有 Renovate プリセットと、GitHub 側で Renovate を回すワークフロー。

## 使い方

各リポジトリの `renovate.json`:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>5ym/renovate"]
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

ほかに `reviewers: ["5ym"]` で PR のレビュワーを指定します。

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
