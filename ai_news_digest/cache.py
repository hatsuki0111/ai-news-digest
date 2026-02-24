"""SQLiteキャッシュ - 重複排除・要約結果キャッシュ"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import Article, ArticleSummary

DEFAULT_DB_PATH = Path(os.environ.get("DIGEST_DATA_DIR", str(Path.home() / "ai-news-digest"))) / "cache.db"


class ArticleCache:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                published TEXT,
                content TEXT,
                language TEXT DEFAULT 'en',
                collected_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS summaries (
                url_hash TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                key_points TEXT NOT NULL,
                importance_score INTEGER DEFAULT 5,
                category TEXT DEFAULT 'その他',
                is_opinion INTEGER DEFAULT 0,
                summarized_at TEXT NOT NULL,
                FOREIGN KEY (url_hash) REFERENCES articles(url_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_articles_collected
                ON articles(collected_at);
        """)
        # マイグレーション: title_ja カラム追加（既存DB対応）
        try:
            self._conn.execute("ALTER TABLE summaries ADD COLUMN title_ja TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合は無視
        self._conn.commit()

    def has_article(self, url_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM articles WHERE url_hash = ?", (url_hash,)
        ).fetchone()
        return row is not None

    def save_article(self, article: Article) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO articles
               (url_hash, url, title, source, published, content, language, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                article.url_hash,
                article.url,
                article.title,
                article.source,
                article.published.isoformat() if article.published else None,
                article.content,
                article.language,
                datetime.now().isoformat(),
            ),
        )
        self._conn.commit()

    def has_summary(self, url_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM summaries WHERE url_hash = ?", (url_hash,)
        ).fetchone()
        return row is not None

    def get_summary(self, url_hash: str, article: Article) -> ArticleSummary | None:
        row = self._conn.execute(
            "SELECT * FROM summaries WHERE url_hash = ?", (url_hash,)
        ).fetchone()
        if row is None:
            return None
        return ArticleSummary(
            article=article,
            summary=row["summary"],
            key_points=json.loads(row["key_points"]),
            importance_score=row["importance_score"],
            category=row["category"],
            is_opinion=bool(row["is_opinion"]) if "is_opinion" in row.keys() else False,
            title_ja=row["title_ja"] if "title_ja" in row.keys() else "",
        )

    def save_summary(self, summary: ArticleSummary) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO summaries
               (url_hash, summary, key_points, importance_score, category, is_opinion, title_ja, summarized_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                summary.article.url_hash,
                summary.summary,
                json.dumps(summary.key_points, ensure_ascii=False),
                summary.importance_score,
                summary.category,
                int(summary.is_opinion),
                summary.title_ja,
                datetime.now().isoformat(),
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
