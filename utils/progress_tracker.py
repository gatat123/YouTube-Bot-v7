"""
실시간 진행 상황 추적 시스템
"""

import asyncio
import discord
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ProgressStage(Enum):
    """진행 단계"""
    CATEGORY_ANALYSIS = ("🔍", "카테고리 분석", 2)
    KEYWORD_EXPANSION = ("🤖", "AI 키워드 확장", 5)
    TRENDS_ANALYSIS = ("📊", "Google Trends 분석", 8)
    YOUTUBE_COLLECTION = ("📺", "YouTube 데이터 수집", 6)
    COMPETITOR_ANALYSIS = ("🏆", "경쟁자 분석", 4)
    FILTERING = ("🔍", "키워드 필터링", 3)
    TITLE_GENERATION = ("💡", "제목 생성", 3)
    REPORT_GENERATION = ("📄", "리포트 생성", 2)
    
    def __init__(self, emoji: str, description: str, duration: int):
        self.emoji = emoji
        self.description = description
        self.duration = duration  # 예상 소요 시간 (초)


class ProgressTracker:
    """Discord 임베드 기반 실시간 진행 상황 추적"""
    
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.start_time = datetime.now()
        self.current_stage: Optional[ProgressStage] = None
        self.completed_stages: List[ProgressStage] = []
        self.stage_start_time: Optional[datetime] = None
        self.progress_message: Optional[discord.InteractionMessage] = None
        self.total_stages = len(ProgressStage)
        self.sub_progress: Dict[str, float] = {}  # 세부 진행률
        
    async def initialize(self, title: str = "YouTube 키워드 분석 중..."):
        """초기 진행 상황 메시지 생성"""
        embed = self._create_progress_embed(title)
        
        if self.interaction.response.is_done():
            self.progress_message = await self.interaction.followup.send(
                embed=embed,
                ephemeral=False
            )
        else:
            await self.interaction.response.send_message(embed=embed)
            self.progress_message = await self.interaction.original_response()
    
    async def update_stage(self, stage: ProgressStage, sub_progress: float = 0.0):
        """새로운 단계로 업데이트"""
        # 이전 단계 완료 처리
        if self.current_stage and self.current_stage not in self.completed_stages:
            self.completed_stages.append(self.current_stage)
        
        self.current_stage = stage
        self.stage_start_time = datetime.now()
        self.sub_progress[stage.name] = sub_progress
        
        await self._update_embed()
    
    async def update_sub_progress(self, progress: float, detail: str = ""):
        """현재 단계의 세부 진행률 업데이트"""
        if self.current_stage:
            self.sub_progress[self.current_stage.name] = progress
            await self._update_embed(detail)
    
    async def complete(self, summary: Dict[str, Any] = None):
        """분석 완료"""
        if self.current_stage and self.current_stage not in self.completed_stages:
            self.completed_stages.append(self.current_stage)
        
        # 완료 임베드 생성
        embed = self._create_completion_embed(summary)
        
        if self.progress_message:
            await self.progress_message.edit(embed=embed)
    
    async def error(self, error_message: str):
        """오류 발생"""
        embed = discord.Embed(
            title="❌ 분석 오류",
            description=f"오류가 발생했습니다: {error_message}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        
        if self.progress_message:
            await self.progress_message.edit(embed=embed)
    
    def _create_progress_embed(self, title: str) -> discord.Embed:
        """진행 상황 임베드 생성"""
        # 전체 진행률 계산
        completed_count = len(self.completed_stages)
        overall_progress = (completed_count / self.total_stages) * 100
        
        # 현재 단계 진행률
        current_progress = 0
        if self.current_stage:
            sub_prog = self.sub_progress.get(self.current_stage.name, 0)
            current_progress = ((completed_count + sub_prog) / self.total_stages) * 100
        
        embed = discord.Embed(
            title=title,
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        # 진행률 바
        progress_bar = self._create_progress_bar(current_progress)
        embed.add_field(
            name=f"전체 진행률: {current_progress:.0f}%",
            value=progress_bar,
            inline=False
        )
        
        # 단계별 상태
        stage_info = []
        for stage in ProgressStage:
            if stage in self.completed_stages:
                status = "✅"
            elif stage == self.current_stage:
                sub_prog = self.sub_progress.get(stage.name, 0)
                status = f"🔄 ({sub_prog*100:.0f}%)"
            else:
                status = "⏳"
            
            stage_info.append(f"{status} {stage.emoji} {stage.description}")
        
        embed.add_field(
            name="진행 단계",
            value="\n".join(stage_info),
            inline=False
        )
        
        # 예상 완료 시간
        if self.current_stage:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            progress_ratio = current_progress / 100 if current_progress > 0 else 0.1
            estimated_total = elapsed / progress_ratio if progress_ratio > 0 else elapsed * 2
            remaining = max(0, estimated_total - elapsed)
            
            eta = datetime.now() + timedelta(seconds=remaining)
            embed.add_field(
                name="예상 완료 시간",
                value=f"{eta.strftime('%H:%M:%S')} (약 {int(remaining)}초 남음)",
                inline=True
            )
        
        # 경과 시간
        elapsed = (datetime.now() - self.start_time).total_seconds()
        embed.add_field(
            name="경과 시간",
            value=f"{int(elapsed)}초",
            inline=True
        )
        
        embed.set_footer(text="YouTube 키워드 분석 봇 v7 | 실시간 업데이트")
        
        return embed
    
    def _create_completion_embed(self, summary: Dict[str, Any] = None) -> discord.Embed:
        """완료 임베드 생성"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        embed = discord.Embed(
            title="✅ 분석 완료!",
            description=f"총 소요 시간: {int(total_time)}초",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        if summary:
            # 분석 요약
            if 'total_keywords' in summary:
                embed.add_field(
                    name="분석 결과",
                    value=f"• 총 키워드: {summary['total_keywords']}개\n"
                          f"• 최종 선별: {summary.get('selected_keywords', 0)}개\n"
                          f"• 생성된 제목: {summary.get('titles_count', 0)}개",
                    inline=False
                )
            
            # 성능 정보
            if 'cache_stats' in summary:
                cache = summary['cache_stats']
                embed.add_field(
                    name="캐시 성능",
                    value=f"• 캐시 히트율: {cache.get('hit_rate', '0%')}\n"
                          f"• 처리 속도 향상: {cache.get('speed_improvement', '0%')}",
                    inline=True
                )
        
        # 단계별 소요 시간
        stage_times = []
        for i, stage in enumerate(self.completed_stages):
            if i < len(self.completed_stages) - 1:
                duration = "✓"
            else:
                duration = f"{stage.duration}s"
            stage_times.append(f"{stage.emoji} {stage.description}: {duration}")
        
        if stage_times:
            embed.add_field(
                name="완료된 작업",
                value="\n".join(stage_times[:5]),  # 최대 5개만 표시
                inline=False
            )
        
        embed.set_footer(text="YouTube 키워드 분석 봇 v7 | 분석 완료")
        
        return embed
    
    def _create_progress_bar(self, percentage: float) -> str:
        """시각적 진행률 바 생성"""
        filled = int(percentage / 5)  # 20칸 중 채워진 칸
        empty = 20 - filled
        
        bar = "█" * filled + "░" * empty
        
        return f"`{bar}`"
    
    async def _update_embed(self, detail: str = ""):
        """임베드 업데이트"""
        if not self.progress_message:
            return
        
        title = "YouTube 키워드 분석 중..."
        if self.current_stage:
            title = f"{self.current_stage.emoji} {self.current_stage.description}"
            if detail:
                title += f" - {detail}"
        
        embed = self._create_progress_embed(title)
        
        try:
            await self.progress_message.edit(embed=embed)
        except discord.errors.NotFound:
            logger.warning("진행 상황 메시지를 찾을 수 없습니다")
        except Exception as e:
            logger.error(f"진행 상황 업데이트 오류: {e}")


class BatchProgressTracker:
    """배치 작업용 진행 상황 추적"""
    
    def __init__(self, total_items: int, update_callback: callable = None):
        self.total_items = total_items
        self.completed_items = 0
        self.update_callback = update_callback
        self.start_time = datetime.now()
        self.item_times: List[float] = []
    
    async def update(self, completed: int = None, increment: int = 1):
        """진행 상황 업데이트"""
        if completed is not None:
            self.completed_items = completed
        else:
            self.completed_items += increment
        
        # 항목당 처리 시간 기록
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.completed_items > 0:
            avg_time = elapsed / self.completed_items
            self.item_times.append(avg_time)
        
        # 콜백 실행
        if self.update_callback:
            progress = self.completed_items / self.total_items if self.total_items > 0 else 0
            await self.update_callback(progress, self.completed_items, self.total_items)
    
    def get_eta(self) -> Optional[datetime]:
        """예상 완료 시간 계산"""
        if not self.item_times or self.completed_items >= self.total_items:
            return None
        
        avg_time = sum(self.item_times) / len(self.item_times)
        remaining_items = self.total_items - self.completed_items
        remaining_seconds = avg_time * remaining_items
        
        return datetime.now() + timedelta(seconds=remaining_seconds)
    
    def get_progress_percentage(self) -> float:
        """진행률 백분율"""
        if self.total_items == 0:
            return 100.0
        return (self.completed_items / self.total_items) * 100
