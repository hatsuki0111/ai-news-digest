# AI News Digest

AIニュースを自動収集・要約・配信するCLIツール。

22のRSSフィードからAI関連記事を収集し、Gemini APIで日本語要約・スコアリングしてTOP10を選定、HTML形式でメール/Slackに配信します。

## Features

- **RSS収集**: OpenAI, Anthropic, Google AI, TechCrunch等 22フィードに対応
- **AI要約**: Gemini 2.5 Flashで日本語要約・キーポイント抽出
- **エンジニア向けスコアリング**: 新モデルリリースや開発ツールを優先的に評価
- **ポエムフィルタ**: 意見記事・エッセイを自動除外
- **重複排除**: SQLiteキャッシュで要約結果を再利用
- **HTMLダイジェスト**: TOP3ヒーローカード + コンパクトリストの3階層テンプレート

## Quick Start

```bash
# 依存インストール
pip install -e .

# 設定ファイル作成
cp config.yaml.example config.yaml
cp .env.example .env
# config.yaml と .env を編集

# 実行
ai-news-digest
```

## Configuration

### 環境変数 (`.env`)

```
GOOGLE_API_KEY=your-gemini-api-key
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 設定ファイル (`config.yaml`)

メール送信先やRSSフィードの追加・有効/無効を管理。`config.yaml.example` を参照。

## Usage

```bash
# 基本実行（過去24時間の記事を収集・要約・送信）
ai-news-digest

# メール送信をスキップ（HTMLファイルのみ生成）
ai-news-digest --no-mail

# 収集のみ（要約・送信をスキップ）
ai-news-digest --skip-summarize

# 対象期間を変更
ai-news-digest --hours 48

# 詳細ログ
ai-news-digest --verbose
```

## Docker

```bash
docker compose up
```

## License

[MIT](LICENSE)
