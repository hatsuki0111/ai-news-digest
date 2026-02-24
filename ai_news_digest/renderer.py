"""Jinja2 HTMLレンダリング"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import DigestReport

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(os.environ.get("DIGEST_OUTPUT_DIR", str(Path.home() / "ai-news-digest" / "output")))


def render_digest(report: DigestReport) -> str:
    """ダイジェストレポートをHTMLにレンダリング"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("digest.html")

    html = template.render(
        date=report.date,
        total_articles=report.total_articles,
        new_articles=report.new_articles,
        top_stories=report.top_stories,
        trend_analysis=report.trend_analysis,
        category_summaries=report.category_summaries,
        all_summaries=report.all_summaries,
    )

    return html


def save_html(html: str, date_str: str | None = None) -> Path:
    """HTMLをローカルに保存"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"digest-{date_str}.html"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(html, encoding="utf-8")
    logger.info("HTML保存: %s", filepath)
    return filepath
