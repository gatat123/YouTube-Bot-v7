"""
예측 엔진 - 간단한 규칙 기반 + 통계적 예측 모델
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import json
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """예측 결과"""
    estimated_views: Tuple[int, int]  # (최소, 최대)
    confidence_score: float  # 0-100
    growth_potential: str  # low, medium, high, viral
    best_upload_time: Dict[str, str]  # 요일별 최적 시간
    estimated_subscriber_gain: int
    competition_level: str  # low, medium, high
    success_probability: float  # 0-100
    recommendations: List[str]


class PredictionEngine:
    """YouTube 성과 예측 엔진"""
    
    def __init__(self):
        # 기본 예측 모델 (규칙 기반)
        self.base_views_by_competition = {
            "low": (5000, 50000),
            "medium": (1000, 20000),
            "high": (100, 5000)
        }
        
        # 카테고리별 성장 배수
        self.category_multipliers = {
            "Gaming": 2.5,
            "Entertainment": 2.0,
            "Education": 1.8,
            "Science & Technology": 1.5,
            "Music": 2.2,
            "How-to & Style": 1.6,
            "News & Politics": 1.3,
            "Sports": 1.7,
            "default": 1.5
        }
        
        # 최적 업로드 시간 (한국 기준)
        self.optimal_upload_times = {
            "monday": ["19:00", "21:00"],
            "tuesday": ["19:00", "21:00"],
            "wednesday": ["19:00", "21:00"],
            "thursday": ["19:00", "21:00"],
            "friday": ["18:00", "20:00", "22:00"],
            "saturday": ["14:00", "16:00", "20:00"],
            "sunday": ["14:00", "16:00", "20:00"]
        }
        
        logger.info("예측 엔진 초기화 완료")
    
    async def predict_performance(self,
                                 keyword_data: Dict,
                                 trend_data: Dict,
                                 competitor_data: Dict,
                                 category: Optional[str] = None) -> PredictionResult:
        """
        키워드 성과 예측
        
        Args:
            keyword_data: 키워드 분석 데이터
            trend_data: 트렌드 데이터
            competitor_data: 경쟁자 분석 데이터
            category: 콘텐츠 카테고리
            
        Returns:
            예측 결과
        """
        # 1. 경쟁도 분석
        competition_level = self._analyze_competition(keyword_data, competitor_data)
        
        # 2. 트렌드 점수 계산
        trend_score = self._calculate_trend_score(trend_data)
        
        # 3. 기본 조회수 예측
        base_views = self.base_views_by_competition[competition_level]
        
        # 4. 카테고리 보정
        category_mult = self.category_multipliers.get(category, 1.5)
        
        # 5. 트렌드 보정
        trend_mult = 1.0 + (trend_score / 100)  # 트렌드 점수를 배수로 변환
        
        # 6. 시즌성 보정
        seasonal_mult = self._get_seasonal_multiplier()
        
        # 7. 최종 조회수 계산
        min_views = int(base_views[0] * category_mult * trend_mult * seasonal_mult)
        max_views = int(base_views[1] * category_mult * trend_mult * seasonal_mult)
        
        # 8. 바이럴 가능성 체크
        viral_potential = self._check_viral_potential(trend_score, competition_level)
        if viral_potential == "high":
            max_views *= 5  # 바이럴 시 5배 증가 가능
        
        # 9. 구독자 증가 예측
        estimated_subscribers = self._estimate_subscriber_gain(
            (min_views, max_views),
            competition_level,
            category
        )
        
        # 10. 성공 확률 계산
        success_probability = self._calculate_success_probability(
            trend_score,
            competition_level,
            viral_potential
        )
        
        # 11. 신뢰도 점수 계산
        confidence = self._calculate_confidence(keyword_data, trend_data)
        
        # 12. 최적 업로드 시간 결정
        best_times = self._get_best_upload_times(category)
        
        # 13. 추천사항 생성
        recommendations = self._generate_recommendations(
            competition_level,
            trend_score,
            viral_potential,
            category
        )
        
        return PredictionResult(
            estimated_views=(min_views, max_views),
            confidence_score=confidence,
            growth_potential=viral_potential,
            best_upload_time=best_times,
            estimated_subscriber_gain=estimated_subscribers,
            competition_level=competition_level,
            success_probability=success_probability,
            recommendations=recommendations
        )
    
    def _analyze_competition(self, keyword_data: Dict, competitor_data: Dict) -> str:
        """경쟁도 분석"""
        # 간단한 규칙 기반 분석
        total_videos = competitor_data.get('total_results', 0)
        avg_views = competitor_data.get('average_views', 0)
        
        if total_videos < 1000:
            return "low"
        elif total_videos < 10000:
            if avg_views > 100000:
                return "high"
            else:
                return "medium"
        else:
            return "high"
    
    def _calculate_trend_score(self, trend_data: Dict) -> float:
        """트렌드 점수 계산 (0-100)"""
        score = 50.0  # 기본 점수
        
        # Google Trends 데이터 반영
        if 'interest_over_time' in trend_data:
            recent_interest = trend_data['interest_over_time'][-5:]  # 최근 5개 데이터
            if recent_interest:
                avg_interest = np.mean(recent_interest)
                score = min(100, avg_interest)
        
        # 상승/하락 트렌드 반영
        if 'trend_direction' in trend_data:
            if trend_data['trend_direction'] == 'rising':
                score = min(100, score * 1.3)
            elif trend_data['trend_direction'] == 'falling':
                score *= 0.7
        
        return score
    
    def _get_seasonal_multiplier(self) -> float:
        """계절성 배수 계산"""
        month = datetime.now().month
        
        # 한국 기준 시즌별 YouTube 시청 패턴
        seasonal_factors = {
            1: 1.2,   # 1월 - 신년 효과
            2: 1.1,   # 2월
            3: 1.0,   # 3월
            4: 0.9,   # 4월
            5: 0.9,   # 5월
            6: 0.95,  # 6월
            7: 1.1,   # 7월 - 여름 휴가
            8: 1.2,   # 8월 - 여름 휴가
            9: 1.0,   # 9월
            10: 1.0,  # 10월
            11: 1.1,  # 11월
            12: 1.3   # 12월 - 연말 효과
        }
        
        return seasonal_factors.get(month, 1.0)
    
    def _check_viral_potential(self, trend_score: float, competition: str) -> str:
        """바이럴 가능성 체크"""
        if trend_score > 80 and competition == "low":
            return "viral"
        elif trend_score > 70 and competition in ["low", "medium"]:
            return "high"
        elif trend_score > 50:
            return "medium"
        else:
            return "low"
    
    def _estimate_subscriber_gain(self, 
                                 views: Tuple[int, int], 
                                 competition: str,
                                 category: Optional[str]) -> int:
        """구독자 증가 예측"""
        avg_views = (views[0] + views[1]) / 2
        
        # 일반적인 전환율 (조회수 -> 구독자)
        conversion_rates = {
            "low": 0.01,      # 1%
            "medium": 0.005,  # 0.5%
            "high": 0.002     # 0.2%
        }
        
        base_rate = conversion_rates[competition]
        
        # 카테고리별 보정
        category_adjustments = {
            "Education": 1.5,
            "How-to & Style": 1.3,
            "Gaming": 0.8,
            "Entertainment": 0.9
        }
        
        adjustment = category_adjustments.get(category, 1.0)
        
        return int(avg_views * base_rate * adjustment)
    
    def _calculate_success_probability(self, 
                                      trend_score: float,
                                      competition: str,
                                      viral_potential: str) -> float:
        """성공 확률 계산"""
        base_probability = 50.0
        
        # 트렌드 점수 반영
        base_probability += (trend_score - 50) * 0.5
        
        # 경쟁도 반영
        competition_adjustment = {
            "low": 20,
            "medium": 0,
            "high": -20
        }
        base_probability += competition_adjustment[competition]
        
        # 바이럴 가능성 반영
        viral_adjustment = {
            "viral": 30,
            "high": 15,
            "medium": 5,
            "low": 0
        }
        base_probability += viral_adjustment[viral_potential]
        
        # 0-100 범위로 제한
        return max(0, min(100, base_probability))
    
    def _calculate_confidence(self, keyword_data: Dict, trend_data: Dict) -> float:
        """예측 신뢰도 계산"""
        confidence = 50.0
        
        # 데이터 품질에 따라 신뢰도 조정
        if keyword_data.get('total_keywords', 0) > 50:
            confidence += 10
        
        if trend_data.get('data_points', 0) > 20:
            confidence += 10
        
        if trend_data.get('regions_data'):
            confidence += 5
        
        # 데이터 일관성 체크
        if keyword_data.get('consistency_score', 0) > 0.7:
            confidence += 10
        
        return min(100, confidence)
    
    def _get_best_upload_times(self, category: Optional[str]) -> Dict[str, str]:
        """최적 업로드 시간 결정"""
        # 카테고리별 특수 시간대
        category_times = {
            "Gaming": {
                "friday": ["20:00", "22:00"],
                "saturday": ["15:00", "20:00", "22:00"],
                "sunday": ["15:00", "20:00"]
            },
            "Education": {
                "monday": ["18:00", "20:00"],
                "tuesday": ["18:00", "20:00"],
                "wednesday": ["18:00", "20:00"]
            }
        }
        
        if category in category_times:
            base_times = self.optimal_upload_times.copy()
            base_times.update(category_times[category])
            return base_times
        
        return self.optimal_upload_times
    
    def _generate_recommendations(self,
                                 competition: str,
                                 trend_score: float,
                                 viral_potential: str,
                                 category: Optional[str]) -> List[str]:
        """맞춤형 추천사항 생성"""
        recommendations = []
        
        # 경쟁도 기반 추천
        if competition == "high":
            recommendations.append("🎯 니치 키워드와 롱테일 키워드에 집중하세요")
            recommendations.append("📊 차별화된 콘텐츠 포맷이나 독특한 관점을 제시하세요")
        elif competition == "low":
            recommendations.append("💎 블루오션 키워드입니다! 빠르게 콘텐츠를 제작하세요")
            recommendations.append("🔄 시리즈물로 제작하여 해당 분야 권위자가 되세요")
        
        # 트렌드 기반 추천
        if trend_score > 70:
            recommendations.append("🔥 급상승 트렌드! 24-48시간 내 업로드를 권장합니다")
            recommendations.append("📱 쇼츠(Shorts)도 함께 제작하여 노출을 극대화하세요")
        elif trend_score < 30:
            recommendations.append("📈 에버그린 콘텐츠로 접근하여 장기적 조회수를 노리세요")
        
        # 바이럴 가능성 기반 추천
        if viral_potential in ["viral", "high"]:
            recommendations.append("🚀 바이럴 가능성 높음! 썸네일과 제목에 특별히 신경쓰세요")
            recommendations.append("💬 커뮤니티 탭과 SNS를 활용한 사전 홍보를 진행하세요")
        
        # 카테고리별 특수 추천
        if category == "Gaming":
            recommendations.append("🎮 실시간 스트리밍과 연계하여 시너지를 만드세요")
        elif category == "Education":
            recommendations.append("📚 자료 다운로드 링크를 제공하여 가치를 높이세요")
        
        return recommendations[:5]  # 최대 5개 추천