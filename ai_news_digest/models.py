"""データクラス定義"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """収集された記事"""

    url: str
    title: str
    source: str
    published: datetime | None = None
    content: str = ""
    language: str = "en"

    @property
    def url_hash(self) -> str:
        import hashlib

        return hashlib.sha256(self.url.encode()).hexdigest()[:16]


@dataclass
class ArticleSummary:
    """個別記事の要約"""

    article: Article
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    importance_score: int = 5
    category: str = "その他"
    is_opinion: bool = False
    title_ja: str = ""


@dataclass
class DigestReport:
    """ダイジェストレポート全体"""

    date: str
    top_stories: list[ArticleSummary] = field(default_factory=list)
    trend_analysis: str = ""
    category_summaries: dict[str, str] = field(default_factory=dict)
    all_summaries: list[ArticleSummary] = field(default_factory=list)
    total_articles: int = 0
    new_articles: int = 0
