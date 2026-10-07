#!/usr/bin/env python3
# forgejo-settings.json を Forgejo(fj.doany.io)に当てる。違うものだけ直し、何を直したかを出す。
# 環境変数: FORGEJO_TOKEN(組織とリポジトリの書き込み)、各 webhook の url_secret の名前の変数。DRY_RUN=true なら読むだけ
import json, os, sys, urllib.request

cfg = json.load(open(os.path.join(os.path.dirname(__file__), "forgejo-settings.json")))
H, ORG, TOKEN = cfg["host"], cfg["org"], os.environ["FORGEJO_TOKEN"]
DRY = os.environ.get("DRY_RUN") == "true"
changed, failed = [], []

def api(method, path, body=None):
    req = urllib.request.Request(f"{H}/api/v1{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            t = r.read()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

def apply(what, method, path, body):
    if DRY:
        changed.append(f"(dry) {what}"); return
    st, res = api(method, path, body)
    (changed if st < 300 else failed).append(f"{what}" + ("" if st < 300 else f" → {st} {res}"))

def diff(have, want):
    return {k: v for k, v in want.items() if have.get(k) != v}

# 1. リポジトリのマージの設定(アーカイブ済みは除く)
page, repos = 1, []
while True:
    st, res = api("GET", f"/orgs/{ORG}/repos?limit=50&page={page}")
    if st != 200: sys.exit(f"repos: {st} {res}")
    repos += res
    if len(res) < 50: break
    page += 1
for r in repos:
    if r.get("archived"): continue
    d = diff(r, cfg["repo"])
    if d: apply(f"{r['full_name']}: {d}", "PATCH", f"/repos/{r['full_name']}", d)

# 2. ブランチの保護(書いてある規則だけ。書いていない規則は消さない)
for repo, rules in cfg["branch_protections"].items():
    st, have = api("GET", f"/repos/{ORG}/{repo}/branch_protections")
    if st != 200: failed.append(f"{repo} protections: {st} {have}"); continue
    byname = {p.get("rule_name") or p.get("branch_name"): p for p in have}
    for rule in rules:
        cur = byname.get(rule["rule_name"])
        if cur is None:
            apply(f"{repo}: 保護 {rule['rule_name']} を作る", "POST", f"/repos/{ORG}/{repo}/branch_protections", rule)
        else:
            d = diff(cur, {k: v for k, v in rule.items() if k != "rule_name"})
            if d: apply(f"{repo}: 保護 {rule['rule_name']} {d}", "PATCH", f"/repos/{ORG}/{repo}/branch_protections/{rule['rule_name']}", d)

# 3. 組織の webhook(**種類ごとに 1 本**の前提で、種類で見分ける。同じ種類を手で足すと上書きされる。書いていない webhook は消さない)
st, hooks = api("GET", f"/orgs/{ORG}/hooks")
if st != 200: sys.exit(f"hooks: {st} {hooks}")
for w in cfg["org_webhooks"]:
    # URL を secrets から取るものは、空なら止める(空の URL で PATCH すると本番の webhook の URL が消える)
    url = os.environ.get(w["url_secret"], "") if "url_secret" in w else w["url"]
    if not url:
        failed.append(f"webhook {w['name']}: secrets の {w.get('url_secret')} が空なので触らない"); continue
    want_cfg = dict(w["config"], url=url)
    body = {"type": w["type"], "config": want_cfg, "events": w["events"], "active": True, "branch_filter": w["branch_filter"]}
    cur = next((h for h in hooks if h["type"] == w["type"]), None)
    if cur is None:
        apply(f"webhook {w['name']} を作る", "POST", f"/orgs/{ORG}/hooks", body); continue
    need = (cur.get("active") is not True or sorted(cur.get("events") or []) != sorted(w["events"])
            or cur.get("branch_filter", "") != w["branch_filter"]
            or any(cur.get("config", {}).get(k) != v for k, v in want_cfg.items()))
    if need:
        shown = {k: cur.get(k) for k in ("active", "events", "branch_filter")}
        shown["config"] = {k: ("(secret)" if k == "url" and "url_secret" in w else v) for k, v in cur.get("config", {}).items()}
        apply(f"webhook {w['name']} を直す(今: {shown})", "PATCH", f"/orgs/{ORG}/hooks/{cur['id']}", {k: v for k, v in body.items() if k != "type"})

for c in changed: print(f"::notice::{c}")
for f in failed: print(f"::error::{f}")
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a") as s: s.write(f"Forgejo: {len(changed)} 件を直した、{len(failed)} 件は失敗\n")
sys.exit(1 if failed else 0)
