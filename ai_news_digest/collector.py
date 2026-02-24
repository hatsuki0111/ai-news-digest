"""RSS/Xフィード収集"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from dateutil import parser as dateutil_parser

from .models import Article

logger = logging.getLogger(__name__)

# AI関連キーワード（大文字小文字不問）
AI_KEYWORDS = re.compile(
    r"(?i)\b("
    r"AI|artificial.intelligence|machine.learning|deep.learning|"
    r"LLM|large.language.model|GPT|Claude|Gemini|ChatGPT|Copilot|"
    r"transformer|diffusion|neural.network|"
    r"OpenAI|Anthropic|DeepMind|Mistral|Meta.AI|"
    r"生成AI|機械学習|深層学習|大規模言語モデル|人工知能"
    r")\b"
)

# AI専門フィード（フィルタ不要）
AI_DEDICATED_SOURCES = {
    "OpenAI Blog", "Anthropic News", "Google AI Blog", "DeepMind",
    "Meta AI", "MIT News - AI", "Hugging Face Blog", "BAIR Blog",
    "TechCrunch - AI", "NVIDIA Blog - AI", "Microsoft AI Blog",
    "Amazon Science", "The Information - AI",
    "ITmedia AI+",
}


def collect_feeds(feed_configs: list[dict], hours: int = 24) -> list[Article]:
    """全フィードから記事を収集する"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles: list[Article] = []

    for feed_cfg in feed_configs:
        if not feed_cfg.get("enabled", True):
            continue
        try:
            new_articles = _fetch_feed(feed_cfg, cutoff)
            articles.extend(new_articles)
            logger.info(
                "%s: %d 件取得", feed_cfg["name"], len(new_articles)
            )
        except Exception:
            logger.exception("フィード取得失敗: %s", feed_cfg["name"])

    logger.info("合計 %d 件の記事を収集", len(articles))
    return articles


def filter_ai_articles(articles: list[Article]) -> list[Article]:
    """AI関連記事のみにフィルタリング"""
    filtered = []
    for article in articles:
        if article.source in AI_DEDICATED_SOURCES:
            filtered.append(article)
            continue
        text = f"{article.title} {article.content}"
        if AI_KEYWORDS.search(text):
            filtered.append(article)

    logger.info("AI関連フィルタ: %d / %d 件", len(filtered), len(articles))
    return filtered


def _fetch_feed(feed_cfg: dict, cutoff: datetime) -> list[Article]:
    """単一フィードから記事を取得"""
    url = feed_cfg["url"]
    source = feed_cfg["name"]
    language = feed_cfg.get("language", "en")

    response = httpx.get(url, timeout=30, follow_redirects=True, headers={
        "User-Agent": "AI-News-Digest/0.1 (+https://github.com/ai-news-digest)"
    })
    response.raise_for_status()

    feed = feedparser.parse(response.text)
    articles: list[Article] = []

    for entry in feed.entries:
        published = _parse_date(entry)
        if published and published < cutoff:
            continue

        content = _extract_content(entry)
        link = entry.get("link", "")
        if not link:
            continue

        articles.append(
            Article(
                url=link,
                title=entry.get("title", "No Title"),
                source=source,
                published=published,
                content=content[:3000],
                language=language,
            )
        )

    return articles


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    """エントリの公開日をパース"""
    for field in ("published", "updated", "created"):
        raw = entry.get(field)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, OverflowError):
                continue
    return None


def _extract_content(entry: feedparser.FeedParserDict) -> str:
    """エントリからコンテンツを抽出"""
    if hasattr(entry, "content") and entry.content:
        return entry.content[0].get("value", "")
    return entry.get("summary", entry.get("description", ""))
