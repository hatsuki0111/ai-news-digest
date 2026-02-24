"""Gemini APIで要約・注目ニュース選定"""

from __future__ import annotations

import json
import logging
import os
import re

from google import genai

from .cache import ArticleCache
from .models import Article, ArticleSummary, DigestReport

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"

# ソース優先度（高いほど重要な情報源）
SOURCE_PRIORITY: dict[str, str] = {
    # 公式ブログ（最高優先）
    "OpenAI Blog": "高",
    "Anthropic News": "高",
    "Google AI Blog": "高",
    "DeepMind": "高",
    "Meta AI": "高",
    "Hugging Face Blog": "高",
    "NVIDIA Blog - AI": "高",
    "Microsoft AI Blog": "高",
    "Amazon Science": "高",
    # メジャーメディア（高優先）
    "TechCrunch - AI": "高",
    "The Information - AI": "高",
    "VentureBeat AI": "高",
    "The Verge - AI": "高",
    "Ars Technica - AI": "高",
    "MIT News - AI": "高",
    # キュレーション型（中〜高優先：人気記事が集まる）
    "はてなブックマーク - 機械学習": "中〜高",
    # 日本語メディア
    "ITmedia AI+": "高",
}


def _get_client() -> genai.Client:
    return genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def summarize_articles(
    articles: list[Article],
    cache: ArticleCache,
) -> list[ArticleSummary]:
    """各記事を個別に要約する（キャッシュ活用）"""
    client = _get_client()
    summaries: list[ArticleSummary] = []

    for article in articles:
        cached = cache.get_summary(article.url_hash, article)
        if cached:
            logger.debug("キャッシュヒット: %s", article.title)
            summaries.append(cached)
            continue

        try:
            summary = _summarize_single(client, article)
            cache.save_summary(summary)
            summaries.append(summary)
            logger.info("要約完了: %s", article.title)
        except Exception:
            logger.exception("要約失敗: %s", article.title)

    return summaries


def generate_digest(summaries: list[ArticleSummary], date: str) -> DigestReport:
    """全要約からダイジェストレポートを生成"""
    if not summaries:
        return DigestReport(date=date, total_articles=0, new_articles=0)

    # ポエム・意見記事を除外
    news_summaries = [s for s in summaries if not s.is_opinion]
    opinion_count = len(summaries) - len(news_summaries)
    if opinion_count:
        logger.info("ポエム・意見記事を除外: %d 件", opinion_count)

    if not news_summaries:
        return DigestReport(date=date, total_articles=len(summaries), new_articles=0)

    client = _get_client()

    summaries_text = "\n\n".join(
        f"[{i}]【{s.article.source}（信頼度: {SOURCE_PRIORITY.get(s.article.source, '中')}）】{s.article.title}\n"
        f"重要度: {s.importance_score}/10 | カテゴリ: {s.category}\n"
        f"要約: {s.summary}\n"
        f"要点: {'; '.join(s.key_points)}\n"
        f"URL: {s.article.url}"
        for i, s in enumerate(news_summaries)
    )

    prompt = f"""以下はAI関連ニュース記事の要約一覧です。最も注目すべき記事を10件選んでください。

{summaries_text}

以下のJSON形式で出力してください:
{{
  "top10_indices": [0, 1, 2, ...]  // 最も注目すべき記事のインデックス（0始まり、最大10件）
}}

選定基準（対象読者: AIエンジニア・開発者チーム）:
1. 新モデル・新機能リリース: 新しいAIモデル（例: GPT-5, Claude Opus, Gemini新版等）やAPIの公開は最優先
2. 開発ツール・フレームワーク: SDK、ライブラリ、開発環境のアップデートや新規公開
3. 技術的ブレークスルー: ベンチマーク更新、新アーキテクチャ、性能改善
4. 実務直結情報: エンジニアが明日の仕事で使える技術情報・ベストプラクティス
5. ソースの信頼度: 公式ブログやメジャーメディア（信頼度: 高）を優先
※ 企業の提携・資金調達・人事・規制などのビジネスニュースは、技術的に重要な場合のみ選定
JSONのみ出力し、それ以外のテキストは含めないでください。"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    result = _parse_json_response(response.text)

    top_indices = result.get("top10_indices", [])[:10]
    top_stories = [news_summaries[i] for i in top_indices if i < len(news_summaries)]
    top_stories.sort(key=lambda s: -s.importance_score)

    sorted_summaries = sorted(news_summaries, key=lambda s: (-s.importance_score, s.category))

    return DigestReport(
        date=date,
        top_stories=top_stories,
        trend_analysis=result.get("trend_analysis", ""),
        category_summaries=result.get("category_summaries", {}),
        all_summaries=sorted_summaries,
        total_articles=len(summaries),
        new_articles=len(summaries),
    )


def _summarize_single(client: genai.Client, article: Article) -> ArticleSummary:
    """単一記事を要約"""
    content_preview = article.content[:2000] if article.content else "(コンテンツなし)"

    source_priority = SOURCE_PRIORITY.get(article.source, "中")

    prompt = f"""以下のAI関連ニュース記事を分析してください。

タイトル: {article.title}
ソース: {article.source}
ソース信頼度: {source_priority}
URL: {article.url}
言語: {article.language}

本文:
{content_preview}

以下のJSON形式で日本語で出力してください:
{{
  "summary": "記事の要約（日本語、200-400文字）",
  "key_points": ["要点1", "要点2", "要点3"],
  "importance_score": 7,  // 1-10のスコア
  "category": "カテゴリ",  // 以下から選択: LLM, 開発ツール, API・SDK, オープンソース, セキュリティ, 企業動向
  "is_opinion": false,  // ポエム・意見記事かどうか
  "title_ja": "タイトルの日本語訳"  // 記事の言語がenの場合のみ、タイトルを自然な日本語に翻訳。jaの場合は空文字列""
}}

is_opinionの判定基準（trueにすべき記事）:
- 個人の感想・エッセイ・ポエム（例:「AIで人生変わった」「エンジニアとは何か」）
- 具体的な技術情報や事実がなく、主観・哲学・精神論が中心の記事
- 自分語り・日記・雑感・書評
- 「〜について思うこと」「〜を考える」系の意見記事
※ 技術的な解説・チュートリアル・製品発表・研究紹介はfalse

importance_scoreの判定基準（エンジニア向け。高スコアから順に）:
- 9-10: 新モデルリリース（例: GPT-5, Claude Opus 4.6, Gemini 2.5等）、主要フレームワーク/ツールの新バージョン
- 8-9: 新API・SDK公開、開発ツールのメジャーアップデート、重要なベンチマーク結果、オープンソースモデル公開
- 7-8: 技術的なチュートリアル・解説、プラットフォームの機能追加、実務に直結する技術情報
- 5-6: 企業の提携・資金調達・人事、規制・政策の動向、業界の一般的なトレンド記事
- 3-4: 市場予測・アナリスト意見、概念的・哲学的な議論
- ソース信頼度も加味: 公式ブログ（高）> メジャーメディア（高）> キュレーション（中〜高）> 個人投稿（低）
JSONのみ出力し、それ以外のテキストは含めないでください。"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    result = _parse_json_response(response.text)

    return ArticleSummary(
        article=article,
        summary=result.get("summary", ""),
        key_points=result.get("key_points", []),
        importance_score=result.get("importance_score", 5),
        category=result.get("category", "その他"),
        is_opinion=result.get("is_opinion", False),
        title_ja=result.get("title_ja", ""),
    )


def _parse_json_response(text: str) -> dict:
    """応答からJSONを抽出・パース"""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text)
