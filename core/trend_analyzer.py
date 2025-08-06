# core/trend_analyzer.py 수정

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import re

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """트렌드 분석 클래스"""
    
    def __init__(self, trends_service, keyword_expander, cache_manager=None):
        self.trends_service = trends_service
        self.keyword_expander = keyword_expander
        self.cache = cache_manager
        
    def filter_keywords_first_pass(self, keywords: List[str], max_keywords: int = 30) -> List[str]:
        """
        1차 키워드 필터링 - 누락된 메서드 추가
        중복 제거, 길이 제한, 특수문자 처리 등
        """
        filtered = []
        seen = set()
        
        for keyword in keywords:
            # 기본 정리
            keyword = keyword.strip()
            
            # 길이 체크 (2-50자)
            if len(keyword) < 2 or len(keyword) > 50:
                continue
                
            # 특수문자 제거 (일부 허용)
            keyword = re.sub(r'[^\w\s\-\_\.\#\@가-힣]', '', keyword)
            
            # 빈 문자열 체크
            if not keyword:
                continue
                
            # 중복 체크 (대소문자 구분 없이)
            normalized = keyword.lower()
            if normalized in seen:
                continue
                
            seen.add(normalized)
            filtered.append(keyword)
            
            # 최대 개수 제한
            if len(filtered) >= max_keywords:
                break
                
        logger.info(f"1차 필터링: {len(keywords)} → {len(filtered)} 키워드")
        return filtered
        
    def filter_keywords_second_pass(self, keywords: List[str], base_keyword: str) -> List[str]:
        """
        2차 키워드 필터링 - 관련성 기반
        """
        filtered = []
        base_lower = base_keyword.lower()
        
        # 관련성 점수 계산
        scored_keywords = []
        for keyword in keywords:
            score = self._calculate_relevance_score(keyword, base_keyword)
            scored_keywords.append((keyword, score))
            
        # 점수 기준 정렬
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 키워드 선택
        for keyword, score in scored_keywords[:20]:
            if score > 0:
                filtered.append(keyword)
                
        logger.info(f"2차 필터링: {len(keywords)} → {len(filtered)} 키워드")
        return filtered
        
    def _calculate_relevance_score(self, keyword: str, base_keyword: str) -> float:
        """키워드 관련성 점수 계산"""
        score = 0.0
        keyword_lower = keyword.lower()
        base_lower = base_keyword.lower()
        
        # 정확히 포함하면 높은 점수
        if base_lower in keyword_lower:
            score += 5.0
            
        # 부분 일치
        for word in base_lower.split():
            if word in keyword_lower:
                score += 2.0
                
        # 길이 페널티 (너무 길면 감점)
        if len(keyword) > 30:
            score -= 1.0
            
        # 특수문자 많으면 감점
        special_chars = len(re.findall(r'[^\w\s가-힣]', keyword))
        score -= special_chars * 0.5
        
        return max(0, score)
        
    async def analyze_trend(self, keyword: str, period: str = 'today 3-m') -> Dict:
        """트렌드 분석 (우회 로직 포함)"""
        try:
            # 캐시 확인
            if self.cache:
                cache_key = f"trend_{keyword}_{period}"
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.info(f"캐시에서 트렌드 데이터 로드: {keyword}")
                    return cached
                    
            # 키워드 확장
            expanded_keywords = self.keyword_expander.expand_keyword(keyword)
            
            # 1차 필터링
            filtered_keywords = self.filter_keywords_first_pass(expanded_keywords)
            
            # 2차 필터링 (관련성)
            final_keywords = self.filter_keywords_second_pass(filtered_keywords, keyword)
            
            # 배치 처리 (5개씩)
            all_data = []
            for i in range(0, len(final_keywords), 5):
                batch = final_keywords[i:i+5]
                if batch:
                    try:
                        data = self.trends_service.get_interest_over_time(batch, period)
                        if data is not None:
                            all_data.append(data)
                    except Exception as e:
                        logger.error(f"배치 처리 실패: {e}")
                        
            # 데이터 병합
            if all_data:
                combined_data = pd.concat(all_data, axis=1)
                # 중복 컬럼 제거
                combined_data = combined_data.loc[:, ~combined_data.columns.duplicated()]
                
                result = self._process_trend_data(combined_data, keyword)
                
                # 캐시 저장
                if self.cache and result:
                    await self.cache.set(cache_key, result, expire=3600)  # 1시간
                    
                return result
            else:
                logger.error(f"❌ 트렌드 데이터 획듍 실패: {keyword}")
                return None  # 실패시 None 반환
                
        except Exception as e:
            logger.error(f"❌ 트렌드 분석 실패: {e}")
            return None  # 실패시 None 반환
            
    def _process_trend_data(self, data: pd.DataFrame, keyword: str) -> Dict:
        """트렌드 데이터 처리"""
        try:
            # 기본 통계
            stats = {}
            for col in data.columns:
                if col != 'isPartial':
                    stats[col] = {
                        'mean': float(data[col].mean()),
                        'max': float(data[col].max()),
                        'min': float(data[col].min()),
                        'std': float(data[col].std()),
                        'trend': self._calculate_trend_direction(data[col])
                    }
                    
            return {
                'keyword': keyword,
                'period': f"{data.index[0]} ~ {data.index[-1]}",
                'stats': stats,
                'top_keywords': sorted(stats.items(), key=lambda x: x[1]['mean'], reverse=True)[:5],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"데이터 처리 실패: {e}")
            return None
            
    def _calculate_trend_direction(self, series: pd.Series) -> str:
        """트렌드 방향 계산"""
        if len(series) < 2:
            return "stable"
            
        # 첫 30%와 마지막 30% 비교
        first_part = series[:int(len(series) * 0.3)].mean()
        last_part = series[-int(len(series) * 0.3):].mean()
        
        if last_part > first_part * 1.1:
            return "rising"
        elif last_part < first_part * 0.9:
            return "falling"
        else:
            return "stable"