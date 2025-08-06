"""
YouTube 키워드 분석 봇 v7 - 메인 파일
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import json
import sys

# 프로젝트 모듈
from config import config
from core import KeywordExpander, TrendAnalyzer, CompetitorAnalyzer, PredictionEngine
from utils import cache_manager, ProgressTracker, ProgressStage, APIManager
from services import YouTubeService, TrendsService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeAnalyzerBot(commands.Bot):
    """YouTube 키워드 분석 봇 v7"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        # 서비스 초기화 (올바른 순서로)
        self.trends_service = TrendsService()
        self.youtube_service = YouTubeService()
        self.api_manager = APIManager()
        self.keyword_expander = KeywordExpander()
        self.competitor_analyzer = CompetitorAnalyzer()
        self.prediction_engine = PredictionEngine()
        
        # TrendAnalyzer 초기화 - 올바른 인자 전달
        self.trend_analyzer = TrendAnalyzer(
            trends_service=self.trends_service,
            youtube_service=self.youtube_service,
            api_manager=self.api_manager,
            progress_tracker=None  # 필요시 추가
        )
        
        logger.info("YouTube 분석 봇 v7 초기화 완료")
    
    async def setup_hook(self):
        """봇 시작 시 설정"""
        # 캐시 매니저 초기화 (PostgreSQL 연결 포함)
        await cache_manager.initialize()
        
        # 슬래시 커맨드 동기화
        await self.tree.sync()
        logger.info("슬래시 커맨드 동기화 완료")
    
    async def on_ready(self):
        """봇 준비 완료"""
        logger.info(f'{self.user} 준비 완료! (v7)')
        
        # 상태 메시지 설정
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="YouTube 트렌드 분석 중 | v7"
            )
        )
        
        # 캐시 통계 로그
        cache_stats = cache_manager.get_stats()
        logger.info(f"캐시 상태: {cache_stats}")
    
    async def close(self):
        """봇 종료 시 정리"""
        await cache_manager.close()
        await super().close()


# 봇 인스턴스
bot = YouTubeAnalyzerBot()


# === 메인 분석 명령어 ===
@bot.tree.command(
    name="analyze",
    description="YouTube 키워드 종합 분석 (v7 - 90개 키워드 확장)"
)
@app_commands.describe(
    content="분석할 주제 또는 설명",
    category="콘텐츠 카테고리",
    keywords="추가 키워드 (쉼표로 구분)",
    depth="분석 깊이 (light/medium/deep)"
)
@app_commands.choices(
    category=[
        app_commands.Choice(name="게임", value="Gaming"),
        app_commands.Choice(name="교육", value="Education"),
        app_commands.Choice(name="엔터테인먼트", value="Entertainment"),
        app_commands.Choice(name="기술", value="Tech"),
        app_commands.Choice(name="브이로그", value="Vlog"),
        app_commands.Choice(name="음식", value="Food")
    ],
    depth=[
        app_commands.Choice(name="빠른 분석 (Light)", value="light"),
        app_commands.Choice(name="표준 분석 (Medium)", value="medium"),
        app_commands.Choice(name="심층 분석 (Deep)", value="deep")
    ]
)
async def analyze_command(
    interaction: discord.Interaction,
    content: str,
    category: Optional[str] = None,
    keywords: Optional[str] = None,
    depth: str = "medium"
):
    """메인 분석 명령어"""
    
    # 즉시 defer로 응답 - 3초 타임아웃 방지
    await interaction.response.defer(thinking=True)
    
    # 진행 상황 추적 시작
    tracker = ProgressTracker(interaction)
    await tracker.initialize("🚀 YouTube 키워드 분석 시작...")
    
    try:
        # 사용자 키워드 파싱
        user_keywords = []
        if keywords:
            user_keywords = [k.strip() for k in keywords.split(',')]
        
        # === Phase 1: 키워드 확장 (20 → 90개) ===
        await tracker.update_stage(ProgressStage.KEYWORD_EXPANSION)
        
        expanded_keywords = await bot.keyword_expander.expand_keywords(
            base_text=content,
            category=category,
            user_keywords=user_keywords
        )
        
        await tracker.update_sub_progress(1.0, f"{len(expanded_keywords)}개 키워드 생성 완료")
        
        # === Phase 2: Google Trends 분석 (비동기 처리) ===
        await tracker.update_stage(ProgressStage.TRENDS_ANALYSIS)
        
        # 배치 진행 상황 업데이트
        async def trends_progress(completed, total):
            progress = completed / total if total > 0 else 0
            await tracker.update_sub_progress(progress, f"{completed}/{total} 배치 분석 중")
        
        # 트렌드 분석 실행 - 비동기 메서드 사용
        trend_results = await bot.trend_analyzer.analyze_keywords(
            keywords=[kw.keyword for kw in expanded_keywords],
            category=category,
            progress_callback=trends_progress
        )
        
        # === Phase 3: 1차 필터링 (90 → 60개) ===
        await tracker.update_stage(ProgressStage.FILTERING)
        
        # TrendAnalysis 객체를 딕셔너리로 변환하여 필터링
        trend_results_dict = [tr.to_dict() for tr in trend_results]
        
        # 기회 점수 기준으로 상위 60개 선별
        filtered_keywords_1st = sorted(
            trend_results_dict,
            key=lambda x: x['opportunity_score'],
            reverse=True
        )[:60]
        
        await tracker.update_sub_progress(0.5, f"1차 필터링 완료: {len(filtered_keywords_1st)}개")
        
        # === Phase 4: YouTube 데이터 수집 ===
        await tracker.update_stage(ProgressStage.YOUTUBE_DATA)
        
        youtube_data = []
        if config.api.youtube_key:
            # YouTube API 호출도 비동기 처리
            youtube_data = await bot.youtube_service.analyze_keywords(
                [kw['keyword'] for kw in filtered_keywords_1st[:30]],  # API 제한
                progress_callback=lambda c, t: asyncio.create_task(
                    tracker.update_sub_progress(c/t, f"{c}/{t} 키워드 분석 중")
                )
            )
        
        # === Phase 5: 경쟁자 분석 ===
        await tracker.update_stage(ProgressStage.COMPETITOR_ANALYSIS)
        
        competitor_data = await bot.competitor_analyzer.analyze_competitors(
            filtered_keywords_1st[:10],  # 상위 10개만
            youtube_data
        )
        
        # === Phase 6: 2차 필터링 (60 → 40개) ===
        await tracker.update_sub_progress(0.8, "2차 정밀 필터링 중...")
        
        # YouTube 데이터 병합
        for kw in filtered_keywords_1st[:30]:
            if kw['keyword'] in youtube_data:
                kw['youtube_metrics'] = youtube_data[kw['keyword']]
        
        # 기회 점수 재계산 후 최종 40개 선별
        final_keywords = sorted(
            filtered_keywords_1st,
            key=lambda x: x['opportunity_score'],
            reverse=True
        )[:40]
        
        # === Phase 7: 예측 분석 ===
        await tracker.update_stage(ProgressStage.PREDICTION)
        
        predictions = []
        for kw in final_keywords[:10]:  # 상위 10개 예측
            prediction = await bot.prediction_engine.predict_performance(
                keyword_data=kw,
                trend_data=kw,  # 이미 트렌드 데이터 포함
                competitor_data=competitor_data.get(kw['keyword'], {}),
                category=category
            )
            predictions.append({
                'keyword': kw['keyword'],
                'prediction': prediction
            })
        
        # === Phase 8: 제목 생성 ===
        await tracker.update_stage(ProgressStage.TITLE_GENERATION)
        
        # Gemini로 제목 생성
        titles = await bot.api_manager.generate_titles(
            keywords=final_keywords[:5],
            content=content,
            category=category
        )
        
        # === 최종 리포트 생성 ===
        await tracker.complete("✅ 분석 완료! 리포트 생성 중...")
        
        # 최종 임베드 생성
        report_embed = create_final_report(
            content=content,
            category=category,
            final_keywords=final_keywords,
            predictions=predictions,
            titles=titles,
            stats={
                'total_expanded': len(expanded_keywords),
                'first_filter': len(filtered_keywords_1st),
                'final_count': len(final_keywords),
                'trends_data': len([t for t in trend_results if t.google_trends and t.google_trends.get('data_points', 0) > 0]),
                'youtube_data': len(youtube_data)
            }
        )
        
        await interaction.followup.send(embed=report_embed)
        
        # 캐시 통계 업데이트
        cache_stats = cache_manager.get_stats()
        logger.info(f"분석 완료 - 캐시 통계: {cache_stats}")
        
    except asyncio.TimeoutError:
        logger.error("분석 타임아웃")
        error_embed = discord.Embed(
            title="⏱️ 시간 초과",
            description="분석이 너무 오래 걸려 중단되었습니다. 다시 시도해주세요.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)
        
    except Exception as e:
        logger.error(f"분석 중 오류 발생: {e}", exc_info=True)
        await tracker.error(f"❌ 오류 발생: {str(e)}")
        
        error_embed = discord.Embed(
            title="❌ 분석 오류",
            description=f"분석 중 문제가 발생했습니다: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)


def create_final_report(content: str, category: Optional[str], 
                       final_keywords: List[Dict], predictions: List[Dict],
                       titles: List[str], stats: Dict) -> discord.Embed:
    """최종 리포트 임베드 생성"""
    
    embed = discord.Embed(
        title="📊 YouTube 키워드 분석 리포트 v7",
        description=f"**주제**: {content}\n**카테고리**: {category or '일반'}",
        color=config.embed_color,
        timestamp=datetime.now()
    )
    
    # 통계 정보
    embed.add_field(
        name="📈 분석 통계",
        value=f"• 확장 키워드: **{stats['total_expanded']}개**\n"
              f"• 1차 필터링: **{stats['first_filter']}개**\n"
              f"• 최종 선별: **{stats['final_count']}개**\n"
              f"• 실제 트렌드 데이터: **{stats['trends_data']}개**",
        inline=False
    )
    
    # 상위 키워드
    top_keywords = []
    for i, kw in enumerate(final_keywords[:10], 1):
        score = kw.get('opportunity_score', 0)
        trend_data = kw.get('google_trends', {})
        trend = trend_data.get('trend_direction', 'stable')
        emoji = "🔥" if trend == "rising" else "📈" if trend == "stable" else "📉"
        top_keywords.append(f"{i}. {emoji} **{kw['keyword']}** (점수: {score:.1f})")
    
    embed.add_field(
        name="🎯 추천 키워드 TOP 10",
        value="\n".join(top_keywords),
        inline=False
    )
    
    # 예측 정보 (상위 3개)
    if predictions:
        prediction_text = []
        for p in predictions[:3]:
            pred = p['prediction']
            views = pred.estimated_views
            prediction_text.append(
                f"**{p['keyword']}**\n"
                f"• 예상 조회수: {views[0]:,} ~ {views[1]:,}\n"
                f"• 성공률: {pred.success_probability:.0f}%\n"
                f"• 성장성: {pred.growth_potential}"
            )
        
        embed.add_field(
            name="🔮 성과 예측",
            value="\n\n".join(prediction_text),
            inline=False
        )
    
    # 추천 제목
    if titles:
        embed.add_field(
            name="💡 추천 제목",
            value="\n".join([f"{i}. {title}" for i, title in enumerate(titles[:3], 1)]),
            inline=False
        )
    
    # 푸터
    embed.set_footer(text="YouTube 키워드 분석 봇 v7 | Powered by Gemini 2.5 Pro")
    
    return embed


# === 캐시 상태 확인 명령어 ===
@bot.tree.command(name="cache_stats", description="캐시 상태 확인")
async def cache_stats_command(interaction: discord.Interaction):
    """캐시 통계 확인"""
    await interaction.response.defer()
    
    stats = cache_manager.get_stats()
    
    embed = discord.Embed(
        title="📊 캐시 상태",
        color=0x00FF00
    )
    
    embed.add_field(
        name="메모리 캐시",
        value=f"• 크기: {stats['memory_cache_size']}\n"
              f"• LRU 캐시: {stats['lru_cache_size']}",
        inline=True
    )
    
    embed.add_field(
        name="성능",
        value=f"• 히트: {stats['hits']}\n"
              f"• 미스: {stats['misses']}\n"
              f"• 히트율: {stats['hit_rate']}",
        inline=True
    )
    
    if stats['db_saves'] > 0:
        embed.add_field(
            name="PostgreSQL 백업",
            value=f"• 저장: {stats['db_saves']}\n"
                  f"• 로드: {stats['db_loads']}",
            inline=True
        )
    
    await interaction.followup.send(embed=embed)


# === 봇 실행 ===
async def main():
    """메인 실행 함수"""
    try:
        # API 키 확인
        missing_keys = config.api.validate()
        if missing_keys:
            logger.error(f"필수 API 키 누락: {', '.join(missing_keys)}")
            logger.error("`.env` 파일을 확인하고 필요한 API 키를 설정해주세요.")
            sys.exit(1)
        
        # 봇 실행
        await bot.start(config.api.discord_token)
        
    except discord.LoginFailure:
        logger.error("Discord 로그인 실패. 봇 토큰을 확인해주세요.")
    except Exception as e:
        logger.error(f"봇 실행 중 오류: {e}", exc_info=True)
    finally:
        await bot.close()


if __name__ == "__main__":
    # Railway 환경에서는 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 봇 실행
    asyncio.run(main())