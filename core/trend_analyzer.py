# core/trend_analyzer.py
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

@dataclass
class TrendAnalysis:
    """트렌드 분석 결과 데이터 클래스"""
    keyword: str
    google_trends: Optional[Dict[str, Any]] = None
    youtube_metrics: Optional[Dict[str, Any]] = None
    social_media: Optional[Dict[str, Any]] = None
    opportunity_score: float = 0.0
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'keyword': self.keyword,
            'google_trends': self.google_trends,
            'youtube_metrics': self.youtube_metrics,
            'social_media': self.social_media,
            'opportunity_score': self.opportunity_score,
            'confidence_score': self.confidence_score
        }

class TrendAnalyzer:
    def __init__(self, trends_service, youtube_service, api_manager, progress_tracker=None):
        self.trends_service = trends_service
        self.youtube_service = youtube_service
        self.api_manager = api_manager
        self.progress_tracker = progress_tracker
        self.logger = logging.getLogger('core.trend_analyzer')
        
    async def analyze_keywords(self, keywords: List[str], category: str = None, 
                             progress_callback=None) -> List[TrendAnalysis]:
        """
        키워드 리스트에 대한 종합적인 트렌드 분석 (비동기)
        
        Args:
            keywords: 분석할 키워드 리스트
            category: 카테고리 정보
            progress_callback: 진행 상황 콜백 함수
            
        Returns:
            List[TrendAnalysis]: 분석 결과 리스트
        """
        self.logger.info(f"🔍 {len(keywords)}개 키워드 트렌드 분석 시작")
        
        analyses = []
        batch_size = 5  # Google Trends API 제한
        
        total_batches = (len(keywords) + batch_size - 1) // batch_size
        
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            try:
                # Google Trends 데이터 수집 (비동기)
                self.logger.info(f"📊 배치 {batch_num}/{total_batches} Google Trends 분석")
                
                # 비동기 호출 사용
                batch_data = await self.trends_service.get_interest_over_time_async(batch)
                
                # 배치 데이터 처리
                for keyword in batch:
                    analysis = TrendAnalysis(keyword=keyword)
                    
                    if not batch_data.empty and keyword in batch_data.columns:
                        analysis.google_trends = {
                            'relative_score': self.trends_service.get_average_interest(batch_data, keyword),
                            'growth_rate': self.trends_service.calculate_growth_rate(batch_data, keyword),
                            'trend_direction': self.trends_service.get_trend_direction(batch_data, keyword),
                            'data_points': len(batch_data)
                        }
                    else:
                        analysis.google_trends = {
                            'relative_score': 0,
                            'growth_rate': 0,
                            'trend_direction': 'no_data',
                            'data_points': 0
                        }
                    
                    analyses.append(analysis)
                
                # 진행 상황 업데이트
                if progress_callback:
                    progress = (batch_num / total_batches) * 100
                    await progress_callback(progress, f"배치 {batch_num}/{total_batches} 완료")
                
                # 배치 간 짧은 대기 (비동기)
                if i + batch_size < len(keywords):
                    await asyncio.sleep(0.5)  # 비동기 sleep 사용
                    
            except Exception as e:
                self.logger.error(f"❌ 배치 {batch_num} 분석 실패: {e}")
                # 실패한 배치의 키워드들에 대해 기본값 설정
                for keyword in batch:
                    analysis = TrendAnalysis(
                        keyword=keyword,
                        google_trends={
                            'relative_score': 0,
                            'growth_rate': 0,
                            'trend_direction': 'error',
                            'data_points': 0
                        }
                    )
                    analyses.append(analysis)
        
        # 기회 점수 계산
        for analysis in analyses:
            analysis.opportunity_score = self._calculate_opportunity_score(analysis)
            analysis.confidence_score = self._calculate_confidence_score(analysis)
        
        self.logger.info(f"✅ 트렌드 분석 완료: {len(analyses)}개 키워드")
        return analyses
    
    def _calculate_opportunity_score(self, analysis: TrendAnalysis) -> float:
        """
        종합적인 기회 점수 계산
        
        Args:
            analysis: 트렌드 분석 결과
            
        Returns:
            float: 0-100 사이의 기회 점수
        """
        score = 0
        weights = {
            'google_trends': 0.5,
            'youtube_metrics': 0.5,
            'social_media': 0.0  # v7에서 제거됨
        }
        
        # Google Trends 점수
        if analysis.google_trends:
            trends_score = 0
            
            # 상대적 인기도
            relative_score = analysis.google_trends.get('relative_score', 0)
            if relative_score > 70:
                trends_score += 20
            elif relative_score > 50:
                trends_score += 15
            elif relative_score > 30:
                trends_score += 10
            elif relative_score > 0:
                trends_score += 5
            
            # 성장률
            growth_rate = analysis.google_trends.get('growth_rate', 0)
            if growth_rate > 50:
                trends_score += 20
            elif growth_rate > 20:
                trends_score += 15
            elif growth_rate > 0:
                trends_score += 10
            elif growth_rate > -20:
                trends_score += 5
            
            # 트렌드 방향
            trend_direction = analysis.google_trends.get('trend_direction', 'unknown')
            if trend_direction == 'rising':
                trends_score += 10
            elif trend_direction == 'stable':
                trends_score += 5
            
            score += trends_score * weights['google_trends']
        
        # YouTube 메트릭 점수
        if analysis.youtube_metrics:
            youtube_score = 0
            
            # 경쟁도
            competition = analysis.youtube_metrics.get('competition', 'medium')
            if competition == 'low':
                youtube_score += 20
            elif competition == 'medium':
                youtube_score += 10
            elif competition == 'high':
                youtube_score += 5
            
            # 검색 결과 수
            search_results = analysis.youtube_metrics.get('search_results', 0)
            if search_results > 10000:
                youtube_score += 15
            elif search_results > 5000:
                youtube_score += 10
            elif search_results > 1000:
                youtube_score += 5
            
            # 평균 조회수
            avg_views = analysis.youtube_metrics.get('avg_views', 0)
            if avg_views > 100000:
                youtube_score += 15
            elif avg_views > 50000:
                youtube_score += 10
            elif avg_views > 10000:
                youtube_score += 5
            
            score += youtube_score * weights['youtube_metrics']
        
        # 정규화
        return min(100, max(0, score))
    
    def _calculate_confidence_score(self, analysis: TrendAnalysis) -> float:
        """
        데이터 신뢰도 점수 계산
        
        Args:
            analysis: 트렌드 분석 결과
            
        Returns:
            float: 0-100 사이의 신뢰도 점수
        """
        confidence = 0
        
        # 데이터 소스별 가중치
        source_weights = {
            'google_trends': 40,
            'youtube': 40,
            'social_media': 20  # v7에서 미사용
        }
        
        # Google Trends 데이터 확인
        if analysis.google_trends and analysis.google_trends.get('data_points', 0) > 0:
            confidence += source_weights['google_trends']
            
            # 데이터 포인트가 많을수록 신뢰도 증가
            data_points = analysis.google_trends.get('data_points', 0)
            if data_points > 90:
                confidence += 10
            elif data_points > 30:
                confidence += 5
        
        # YouTube 데이터 확인
        if analysis.youtube_metrics and analysis.youtube_metrics.get('search_results', 0) > 0:
            confidence += source_weights['youtube']
        
        return min(100, confidence)