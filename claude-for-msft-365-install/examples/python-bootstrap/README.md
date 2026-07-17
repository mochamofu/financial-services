# ブートストラップエンドポイント — Python リファレンス実装

Claude in Office の `/bootstrap` エンドポイントの最小限の FastAPI 実装です。呼び出し元の Entra ID トークンを検証し、シンプルな先勝ちマッチの RBAC テーブルに基づいて、従業員ごとの `skills` と `mcp_servers` を返します。

## 実際の Entra テナントに対して実行する

```bash
pip install -r requirements.txt
# テナント ID の確認:
python get_tenant_id.py you@yourcompany.com
export TENANT_ID=<your-tenant-guid>
python app.py
```

## 偽トークンでローカル実行する

```bash
pip install -r requirements.txt
export TENANT_ID=dev-tenant
TOKEN=$(python mint_dev_token.py --oid alice --group investment-banking)
DEV_JWKS_PATH=dev_jwks.json python app.py &
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Claude-User-Agent: claude-word/1.0.0" \
     http://127.0.0.1:8080/bootstrap
```

## カスタマイズ

変更が必要なものはすべて **`config.py`** にあります — `app.py` の編集は不要のはずです。

- `SKILLS` と `MCP_SERVERS` を編集 — 配布可能なフルカタログです。
- `RULES` を編集 — 最初にマッチしたルールが適用されます。末尾の空の `when: {}` がデフォルトです。
- `RULES` 内のプレースホルダーのグループ名/ユーザー名を、実際の Entra Object ID(GUID)に置き換えてください。
- グループメンバーシップはトークンの `groups` クレームから読み取ります。テナントがこれを発行しない場合は、`app.py` の `groups = ...` の行を社内ディレクトリへの照会に差し替えてください。
- ルールは `"app": "word" | "excel" | "powerpoint"` で Office ホストごとにスコープできます。アドインが送信する `X-Claude-User-Agent` ヘッダーからパースされます。
- `groups` クレームはデフォルトでは Entra トークンに**含まれません**。対象アプリの *App registration → Token configuration → Add groups claim* で有効化してください。
- インメモリの `RULES` を、実際の真実のソース(DB、設定サービスなど)に差し替えてください。

## セキュリティ

`DEV_JWKS_PATH` を設定すると、サーバーは Microsoft の署名鍵ではなく自己発行の署名鍵を信頼します。`127.0.0.1` にバインドされていない限り起動を拒否します。デプロイ環境では**絶対に**設定しないでください。
