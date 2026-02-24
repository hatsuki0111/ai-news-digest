"""CLIエントリポイント"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

import yaml

from .cache import ArticleCache
from .collector import collect_feeds, filter_ai_articles
from .mailer import send_digest_email
from .renderer import render_digest, save_html
from .summarizer import generate_digest, summarize_articles

logger = logging.getLogger("ai_news_digest")

DEFAULT_CONFIG = Path(os.environ.get("DIGEST_CONFIG", str(Path.home() / "ai-news-digest" / "config.yaml")))


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="AI News Digest - AIニュースを自動収集・要約・配信"
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG, help="設定ファイルパス"
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="収集対象の時間範囲（デフォルト24時間）"
    )
    parser.add_argument(
        "--no-mail", action="store_true", help="メール送信をスキップ"
    )
    parser.add_argument(
        "--skip-summarize", action="store_true", help="要約・送信をスキップ（収集のみ）"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="詳細ログ出力"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 設定読み込み
    config = load_config(args.config)
    today = datetime.now().strftime("%Y-%m-%d")

    # キャッシュ初期化
    cache = ArticleCache()

    try:
        # 1. 記事収集
        logger.info("=== 記事収集開始 (過去%d時間) ===", args.hours)
        feeds = config.get("feeds", [])
        articles = collect_feeds(feeds, hours=args.hours)

        # AI関連フィルタ
        articles = filter_ai_articles(articles)

        # 新着判定＆キャッシュ保存
        new_articles = []
        for article in articles:
            if not cache.has_article(article.url_hash):
                new_articles.append(article)
            cache.save_article(article)

        logger.info("新着記事: %d / %d 件", len(new_articles), len(articles))

        if args.skip_summarize:
            logger.info("--skip-summarize: 要約・送信をスキップ")
            return

        if not articles:
            logger.info("記事がありません。終了します。")
            return

        # 2. 個別記事要約
        logger.info("=== 記事要約開始 ===")
        summaries = summarize_articles(articles, cache)

        # 3. ダイジェスト生成
        logger.info("=== ダイジェスト生成 ===")
        report = generate_digest(summaries, today)
        report.total_articles = len(articles)
        report.new_articles = len(new_articles)

        # 4. HTMLレンダリング
        logger.info("=== HTMLレンダリング ===")
        html = render_digest(report)

        # 5. ローカル保存
        saved_path = save_html(html, today)
        logger.info("HTML保存先: %s", saved_path)

        # 6. メール送信
        if not args.no_mail:
            email_config = config.get("email", {})
            subject_fmt = email_config.get("subject_format", "AI News Digest - {date}")
            subject = subject_fmt.format(date=today)
            logger.info("=== メール送信 ===")
            send_digest_email(html, subject, email_config)
        else:
            logger.info("--no-mail: メール送信をスキップ")

        logger.info("=== 完了 ===")

    finally:
        cache.close()


if __name__ == "__main__":
    main()
