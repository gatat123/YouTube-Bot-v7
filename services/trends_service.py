"""
Google Trends 서비스 - 실제 데이터 검증 강화
"""

from typing import List, Dict, Any, Optional, Tuple
from pytrends.request import TrendReq
import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime, timedelta
import time
import random

from config import config
from utils import cache_manager

logger = logging.getLogger(__name__)


class TrendsService:
    """Google Trends API 서비스 - 실제 데이터 보장"""
    
    def __init__(self):
        # 여러 프록시/헤더 옵션으로 시도
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        
        # 기본 TrendReq 초기화
        self._init_pytrends()
        
        # 앵커 키워드 (비교 기준)
        self.anchor_keywords = {
            'general': '유튜브',
            'game': '게임',
            'food': '요리',
            'vlog': '일상',
            'beauty': '화장품',
            'education': '공부',
            'tech': '스마트폰',
            'music': '음악'
        }
        
        # 재시도 설정
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info("Google Trends 서비스 초기화 완료 (실제 데이터 모드)")
    
    def _init_pytrends(self):
        """PyTrends 초기화 with 랜덤 User-Agent"""
        user_agent = random.choice(self.user_agents)
        self.pytrends = TrendReq(
            hl='ko',  # 한국어
            tz=540,   # 한국 시간대 (UTC+9)
            timeout=(10, 25),
            proxies=[],
            retries=2,
            backoff_factor=0.5,
            requests_args={'headers': {'User-Agent': user_agent}}
        )
    
    async def analyze_keywords_batch(self, 
                                   keywords: List[str], 
                                   category: Optional[str] = None) -> List[Dict[str, Any]]:
        """키워드 배치 분석 - 실제 데이터 보장"""
        results = []
        
        # 카테고리별 앵커 선택
        anchor = self._select_anchor(category)
        
        # 배치 처리 (Google Trends는 최대 5개)
        batch_size = 4  # 앵커 포함 5개
        
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i+batch_size]
            
            # 실제 데이터 가져오기 시도
            batch_result = await self._get_real_trends_data(batch, anchor)
            
            if batch_result:
                results.extend(batch_result)
            else:
                # 실패 시 기본값 제공 (하지만 실제 데이터임을 표시)
                logger.warning(f"Trends 데이터 수집 실패: {batch}")
                results.extend(self._generate_fallback_data(batch, is_real=False))
            
            # API 제한 회피를 위한 지연
            await asyncio.sleep(random.uniform(1, 3))
        
        return results
    
    async def _get_real_trends_data(self, keywords: List[str], anchor: str) -> Optional[List[Dict]]:
        """실제 Google Trends 데이터 가져오기"""
        for attempt in range(self.max_retries):
            try:
                # 키워드 리스트 준비 (앵커 포함)
                kw_list = [anchor] + keywords
                
                # Google Trends 데이터 요청
                logger.info(f"Google Trends 요청: {kw_list}")
                
                # 비동기로 실행
                result = await asyncio.to_thread(
                    self._fetch_trends_data,
                    kw_list
                )
                
                if result:
                    logger.info(f"실제 Trends 데이터 수집 성공: {len(result)} 키워드")
                    return result
                
            except Exception as e:
                logger.error(f"Trends API 오류 (시도 {attempt + 1}): {e}")
                
                # User-Agent 변경 후 재시도
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    self._init_pytrends()  # 새로운 User-Agent로 재초기화
        
        return None
    
    def _fetch_trends_data(self, kw_list: List[str]) -> List[Dict]:
        """동기적으로 Trends 데이터 가져오기"""
        try:
            # 1. Interest Over Time (시간별 관심도)
            self.pytrends.build_payload(
                kw_list,
                timeframe='today 3-m',  # 최근 3개월
                geo='KR',  # 한국
                gprop=''   # 전체 검색
            )
            
            interest_df = self.pytrends.interest_over_time()
            
            # 데이터가 없으면 None 반환
            if interest_df.empty:
                logger.warning("Interest over time 데이터 없음")
                return self._try_alternative_fetch(kw_list)
            
            # 2. Related Queries (연관 검색어)
            related_queries = self.pytrends.related_queries()
            
            # 3. Interest by Region (지역별 관심도)
            try:
                region_df = self.pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True)
            except:
                region_df = pd.DataFrame()
            
            # 결과 포맷팅
            results = []
            for keyword in kw_list[1:]:  # 앵커 제외
                if keyword in interest_df.columns:
                    keyword_data = {
                        'keyword': keyword,
                        'is_real_data': True,
                        'interest_over_time': interest_df[keyword].tolist(),
                        'average_interest': float(interest_df[keyword].mean()),
                        'max_interest': float(interest_df[keyword].max()),
                        'trend_direction': self._calculate_trend_direction(interest_df[keyword]),
                        'related_queries': self._extract_related_queries(related_queries, keyword),
                        'volatility': float(interest_df[keyword].std()),
                        'recent_growth': self._calculate_recent_growth(interest_df[keyword]),
                        'data_timestamp': datetime.now().isoformat()
                    }
                    
                    # 지역 데이터 추가
                    if not region_df.empty and keyword in region_df.columns:
                        keyword_data['regional_interest'] = region_df[keyword].to_dict()
                    
                    results.append(keyword_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Trends 데이터 가져오기 실패: {e}")
            return []
    
    def _try_alternative_fetch(self, kw_list: List[str]) -> List[Dict]:
        """대체 방법으로 데이터 가져오기"""
        results = []
        
        # 키워드 하나씩 시도
        for keyword in kw_list[1:]:  # 앵커 제외
            try:
                self.pytrends.build_payload(
                    [keyword],
                    timeframe='today 1-m',  # 더 짧은 기간
                    geo='KR'
                )
                
                interest_df = self.pytrends.interest_over_time()
                
                if not interest_df.empty and keyword in interest_df.columns:
                    results.append({
                        'keyword': keyword,
                        'is_real_data': True,
                        'interest_over_time': interest_df[keyword].tolist(),
                        'average_interest': float(interest_df[keyword].mean()),
                        'max_interest': float(interest_df[keyword].max()),
                        'trend_direction': self._calculate_trend_direction(interest_df[keyword]),
                        'data_source': 'alternative_fetch',
                        'data_timestamp': datetime.now().isoformat()
                    })
                    
                time.sleep(0.5)  # 짧은 지연
                
            except Exception as e:
                logger.error(f"대체 fetch 실패 ({keyword}): {e}")
                continue
        
        return results
    
    def _calculate_trend_direction(self, series: pd.Series) -> str:
        """트렌드 방향 계산"""
        if len(series) < 2:
            return "stable"
        
        # 최근 데이터와 과거 데이터 비교
        recent = series[-10:].mean() if len(series) >= 10 else series[-len(series)//2:].mean()
        past = series[:10].mean() if len(series) >= 10 else series[:len(series)//2].mean()
        
        if recent > past * 1.2:
            return "rising"
        elif recent < past * 0.8:
            return "falling"
        else:
            return "stable"
    
    def _calculate_recent_growth(self, series: pd.Series) -> float:
        """최근 성장률 계산"""
        if len(series) < 2:
            return 0.0
        
        recent = series[-5:].mean() if len(series) >= 5 else series[-1]
        past = series[-10:-5].mean() if len(series) >= 10 else series[0]
        
        if past == 0:
            return 0.0
        
        return ((recent - past) / past) * 100
    
    def _extract_related_queries(self, related_queries: Dict, keyword: str) -> List[str]:
        """연관 검색어 추출"""
        queries = []
        
        if keyword in related_queries:
            # Top queries
            if 'top' in related_queries[keyword] and related_queries[keyword]['top'] is not None:
                top_df = related_queries[keyword]['top']
                if not top_df.empty:
                    queries.extend(top_df['query'].head(5).tolist())
            
            # Rising queries
            if 'rising' in related_queries[keyword] and related_queries[keyword]['rising'] is not None:
                rising_df = related_queries[keyword]['rising']
                if not rising_df.empty:
                    queries.extend(rising_df['query'].head(3).tolist())
        
        return list(set(queries))[:8]  # 최대 8개
    
    def _generate_fallback_data(self, keywords: List[str], is_real: bool = False) -> List[Dict]:
        """폴백 데이터 생성 (실제 데이터 수집 실패 시)"""
        results = []
        
        for keyword in keywords:
            results.append({
                'keyword': keyword,
                'is_real_data': is_real,
                'average_interest': 50,
                'max_interest': 75,
                'trend_direction': 'stable',
                'error': 'Google Trends 데이터 수집 실패',
                'fallback': True,
                'data_timestamp': datetime.now().isoformat()
            })
        
        return results
    
    def _select_anchor(self, category: Optional[str]) -> str:
        """카테고리별 앵커 키워드 선택"""
        if category and category.lower() in self.anchor_keywords:
            return self.anchor_keywords[category.lower()]
        return self.anchor_keywords['general']
    
    async def get_trending_topics(self, region: str = 'KR') -> List[Dict]:
        """현재 트렌딩 토픽 가져오기"""
        try:
            trending = await asyncio.to_thread(
                self.pytrends.trending_searches,
                pn='south_korea'
            )
            
            if not trending.empty:
                topics = trending[0].head(20).tolist()
                return [
                    {
                        'topic': topic,
                        'rank': i + 1,
                        'is_real_data': True
                    }
                    for i, topic in enumerate(topics)
                ]
        except Exception as e:
            logger.error(f"트렌딩 토픽 가져오기 실패: {e}")
        
        return []
    
    async def get_youtube_search_trends(self, keywords: List[str]) -> List[Dict]:
        """YouTube 특화 트렌드 분석"""
        results = []
        
        for keyword in keywords[:10]:  # 최대 10개
            try:
                # YouTube 검색 트렌드
                self.pytrends.build_payload(
                    [keyword],
                    timeframe='today 1-m',
                    geo='KR',
                    gprop='youtube'  # YouTube 검색만
                )
                
                interest_df = self.pytrends.interest_over_time()
                
                if not interest_df.empty:
                    results.append({
                        'keyword': keyword,
                        'youtube_interest': float(interest_df[keyword].mean()),
                        'youtube_trend': self._calculate_trend_direction(interest_df[keyword]),
                        'is_real_data': True
                    })
                
                await asyncio.sleep(1)  # API 제한 회피
                
            except Exception as e:
                logger.error(f"YouTube 트렌드 분석 실패 ({keyword}): {e}")
                continue
        
        return results