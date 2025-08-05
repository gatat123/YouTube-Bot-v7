"""
트렌드 분석 엔진 - 통합 분석
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import logging

from services import YouTubeService, TrendsService, TikTokService, TwitterService
from utils import cache_manager, BatchProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class TrendAnalysis:
    """트렌드 분석 결과"""
    keyword: str
    opportunity_score: float = 0.0
    relative_score: float = 50.0
    growth_rate: float = 0.0
    trend_direction: str = 'stable'
    competition: str = 'medium'
    confidence: float = 0.0
    
    # 상세 메트릭
    youtube_metrics: Dict = field(default_factory=dict)
    google_trends: Dict = field(default_factory=dict)
    social_metrics: Dict = field(default_factory=dict)
    
    # 메타데이터
    category: Optional[str] = None
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    data_sources: List[str] = field(default_factory=list)


class TrendAnalyzer:
    """통합 트렌드 분석기"""
    
    def __init__(self):
        self.youtube = YouTubeService()
        self.trends = TrendsService()
        self.tiktok = TikTokService()
        self.twitter = TwitterService()
    
    async def analyze_keywords(self, 
                             keywords: List[str],
                             category: Optional[str] = None,
                             progress_callback: Optional[callable] = None) -> List[TrendAnalysis]:
        """키워드 리스트 종합 분석"""
        
        # 진행 상황 추적
        tracker = BatchProgressTracker(len(keywords) * 3, progress_callback)  # 3개 서비스
        
        results = []
        
        # 배치 처리
        batch_size = 5
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i+batch_size]
            
            # 병렬 분석 작업
            tasks = []
            for keyword in batch:
                task = self._analyze_single_keyword(keyword, category, tracker)
                tasks.append(task)
            
            # 배치 실행
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 처리
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"키워드 분석 오류 ({batch[j]}): {result}")
                    results.append(self._get_default_analysis(batch[j], category))
                else:
                    results.append(result)
        
        # 상대적 점수 조정
        self._adjust_relative_scores(results)
        
        # 기회 점수로 정렬
        results.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        return results
    
    async def _analyze_single_keyword(self, 
                                    keyword: str,
                                    category: Optional[str],
                                    tracker: BatchProgressTracker) -> TrendAnalysis:
        """단일 키워드 분석"""
        
        analysis = TrendAnalysis(keyword=keyword, category=category)
        
        # 1. Google Trends 분석
        try:
            trends_data = await self.trends.analyze_keywords_batch([keyword], category)
            if trends_data:
                analysis.google_trends = trends_data[0]
                analysis.relative_score = trends_data[0].get('relative_score', 50)
                analysis.growth_rate = trends_data[0].get('growth_rate', 0)
                analysis.trend_direction = trends_data[0].get('trend', 'stable')
                analysis.data_sources.append('google_trends')
        except Exception as e:
            logger.error(f"Trends 분석 오류 ({keyword}): {e}")
        
        await tracker.update()
        
        # 2. YouTube 메트릭
        try:
            youtube_data = await self.youtube.get_comprehensive_metrics(keyword)
            analysis.youtube_metrics = youtube_data
            analysis.competition = youtube_data.get('competition', 'medium')
            analysis.data_sources.append('youtube')
        except Exception as e:
            logger.error(f"YouTube 분석 오류 ({keyword}): {e}")
        
        await tracker.update()
        
        # 3. 소셜 미디어 (TikTok, Twitter)
        social_tasks = [
            self._get_social_metrics(keyword)
        ]
        
        social_results = await asyncio.gather(*social_tasks, return_exceptions=True)
        
        if not isinstance(social_results[0], Exception):
            analysis.social_metrics = social_results[0]
            if social_results[0]:
                analysis.data_sources.append('social_media')
        
        await tracker.update()
        
        # 4. 종합 점수 계산
        analysis.opportunity_score = self._calculate_opportunity_score(analysis)
        analysis.confidence = self._calculate_confidence(analysis)
        
        return analysis
    
    async def _get_social_metrics(self, keyword: str) -> Dict[str, Any]:
        """소셜 미디어 메트릭 수집"""
        metrics = {}
        
        # TikTok 분석
        try:
            tiktok_viral = await self.tiktok.analyze_viral_potential(keyword)
            metrics['tiktok'] = tiktok_viral
        except Exception as e:
            logger.debug(f"TikTok 분석 실패: {e}")
        
        # Twitter 분석
        try:
            twitter_sentiment = await self.twitter.analyze_sentiment(keyword)
            metrics['twitter'] = twitter_sentiment
        except Exception as e:
            logger.debug(f"Twitter 분석 실패: {e}")
        
        return metrics
    
    def _calculate_opportunity_score(self, analysis: TrendAnalysis) -> float:
        """종합 기회 점수 계산"""
        score = 0
        weight_sum = 0
        
        # Google Trends 점수 (40%)
        if analysis.google_trends:
            trends_score = 0
            
            # 상대적 인기도
            relative = analysis.relative_score
            if relative > 70:
                trends_score += 20
            elif relative > 50:
                trends_score += 15
            elif relative > 30:
                trends_score += 10
            else:
                trends_score += 5
            
            # 성장률
            growth = analysis.growth_rate
            if growth > 50:
                trends_score += 20
            elif growth > 20:
                trends_score += 15
            elif growth > 0:
                trends_score += 10
            elif growth > -20:
                trends_score += 5
            
            score += trends_score
            weight_sum += 40
        
        # YouTube 점수 (40%)
        if analysis.youtube_metrics:
            youtube_score = 0
            
            # 경쟁도
            competition_scores = {'low': 20, 'medium': 10, 'high': 5}
            youtube_score += competition_scores.get(analysis.competition, 10)
            
            # YouTube 기회 점수
            yt_opportunity = analysis.youtube_metrics.get('opportunity', 50)
            youtube_score += yt_opportunity * 0.2
            
            score += youtube_score
            weight_sum += 40
        
        # 소셜 미디어 점수 (20%)
        if analysis.social_metrics:
            social_score = 0
            
            # TikTok 바이럴 점수
            if 'tiktok' in analysis.social_metrics:
                viral_score = analysis.social_metrics['tiktok'].get('viral_score', 50)
                social_score += viral_score * 0.1
            
            # Twitter 버즈 점수
            if 'twitter' in analysis.social_metrics:
                buzz_score = analysis.social_metrics['twitter'].get('buzz_score', 50)
                social_score += buzz_score * 0.1
            
            score += social_score
            weight_sum += 20
        
        # 정규화
        if weight_sum > 0:
            normalized_score = (score / weight_sum) * 100
            return min(100, max(0, normalized_score))
        
        return 50.0
    
    def _calculate_confidence(self, analysis: TrendAnalysis) -> float:
        """분석 신뢰도 계산"""
        confidence = 0
        
        # 데이터 소스별 신뢰도
        source_weights = {
            'google_trends': 40,
            'youtube': 40,
            'social_media': 20
        }
        
        for source, weight in source_weights.items():
            if source in analysis.data_sources:
                confidence += weight
        
        # 데이터 포인트 보너스
        if analysis.google_trends.get('data_points', 0) > 90:
            confidence += 10
        elif analysis.google_trends.get('data_points', 0) > 30:
            confidence += 5
        
        return min(100, confidence)
    
    def _adjust_relative_scores(self, analyses: List[TrendAnalysis]):
        """상대적 점수 조정"""
        if not analyses:
            return
        
        # 최고/최저 점수 찾기
        scores = [a.opportunity_score for a in analyses]
        max_score = max(scores) if scores else 100
        min_score = min(scores) if scores else 0
        
        if max_score == min_score:
            return
        
        # 0-100 스케일로 정규화
        for analysis in analyses:
            normalized = (analysis.opportunity_score - min_score) / (max_score - min_score)
            analysis.relative_score = normalized * 100
    
    def _get_default_analysis(self, keyword: str, category: Optional[str]) -> TrendAnalysis:
        """기본 분석 결과"""
        return TrendAnalysis(
            keyword=keyword,
            category=category,
            opportunity_score=50.0,
            relative_score=50.0,
            growth_rate=0.0,
            trend_direction='stable',
            competition='unknown',
            confidence=0.0
        )
    
    async def get_trending_opportunities(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """현재 트렌딩 기회 발견"""
        opportunities = []
        
        # Google Trends 실시간 트렌드
        try:
            trending_topics = await self.trends.get_trending_topics()
            
            for topic in trending_topics[:10]:
                # 각 트렌딩 토픽 빠른 분석
                analysis = await self._analyze_single_keyword(
                    topic['topic'],
                    category,
                    BatchProgressTracker(1)
                )
                
                if analysis.opportunity_score > 70:
                    opportunities.append({
                        'keyword': topic['topic'],
                        'opportunity_score': analysis.opportunity_score,
                        'source': 'google_trends',
                        'urgency': 'high',
                        'recommended_action': self._get_recommended_action(analysis)
                    })
        
        except Exception as e:
            logger.error(f"트렌딩 기회 분석 오류: {e}")
        
        return opportunities
    
    def _get_recommended_action(self, analysis: TrendAnalysis) -> str:
        """추천 액션 생성"""
        if analysis.opportunity_score > 80 and analysis.competition == 'low':
            return "🔥 즉시 콘텐츠 제작 추천! 블루오션 기회"
        elif analysis.opportunity_score > 70 and analysis.growth_rate > 30:
            return "📈 급성장 키워드! 빠른 대응 필요"
        elif analysis.opportunity_score > 60:
            return "✅ 좋은 기회. 계획적 접근 추천"
        else:
            return "📊 지속 모니터링 필요"
