# services/trends_service.py
import asyncio
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from pytrends.request import TrendReq
import time
from datetime import datetime, timedelta
import random
from functools import lru_cache
import numpy as np

class TrendsService:
    def __init__(self):
        self.logger = logging.getLogger('services.trends_service')
        self.pytrends = None
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 최소 요청 간격 (초)
        self._initialize_pytrends()
        
    def _initialize_pytrends(self):
        """pytrends 초기화 (한국 설정)"""
        try:
            self.pytrends = TrendReq(hl='ko', tz=540, geo='KR')
            self.logger.info("✅ pytrends 초기화 성공 (KR 전용)")
        except Exception as e:
            self.logger.error(f"❌ pytrends 초기화 실패: {e}")
            # 실패 시 기본 설정으로 재시도
            self.pytrends = TrendReq()
    
    async def get_interest_over_time_async(self, keywords: List[str]) -> pd.DataFrame:
        """
        비동기 버전의 Google Trends 데이터 수집
        
        Args:
            keywords: 분석할 키워드 리스트 (최대 5개)
            
        Returns:
            pd.DataFrame: 시간별 관심도 데이터
        """
        if not keywords:
            return pd.DataFrame()
            
        # 키워드 수 제한
        keywords = keywords[:5]
        
        # API 호출 제한 처리 (비동기)
        await self._rate_limit_async()
        
        max_retries = 10
        for attempt in range(max_retries):
            try:
                # pytrends는 동기 라이브러리이므로 run_in_executor 사용
                loop = asyncio.get_event_loop()
                
                # 동기 함수를 비동기로 실행
                result = await loop.run_in_executor(
                    None,
                    self._get_trends_data_sync,
                    keywords
                )
                
                if result is not None and not result.empty:
                    self.logger.info(f"✅ Google Trends 데이터 수집 성공: {len(keywords)}개 키워드")
                    return result
                else:
                    self.logger.warning(f"⚠️ 빈 데이터 (시도 {attempt + 1})")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ API 에러 (시도 {attempt + 1}): {str(e)}")
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = min(60 * (2 ** attempt), 300)  # 최대 5분
                    self.logger.info(f"⏳ Rate limit 대기: {wait_time}초")
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(5 * (attempt + 1))
        
        self.logger.error(f"❌ 모든 시도 실패")
        return pd.DataFrame()
    
    def _get_trends_data_sync(self, keywords: List[str]) -> pd.DataFrame:
        """동기 방식의 트렌드 데이터 수집 (executor에서 실행용)"""
        self.pytrends.build_payload(
            keywords, 
            cat=0, 
            timeframe='today 3-m',  # 최근 3개월
            geo='KR', 
            gprop=''
        )
        return self.pytrends.interest_over_time()
    
    async def _rate_limit_async(self):
        """비동기 API 호출 제한"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            await asyncio.sleep(wait_time)  # 비동기 sleep 사용
        
        self.last_request_time = time.time()
    
    def get_interest_over_time(self, keywords: List[str]) -> pd.DataFrame:
        """
        동기 버전 (레거시 지원용) - 비동기 버전 사용 권장
        """
        # 비동기 함수를 동기로 실행 (권장하지 않음)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 루프가 있으면 새 태스크 생성
                future = asyncio.ensure_future(self.get_interest_over_time_async(keywords))
                return loop.run_until_complete(future)
            else:
                return asyncio.run(self.get_interest_over_time_async(keywords))
        except Exception as e:
            self.logger.error(f"동기 호출 중 오류: {e}")
            return pd.DataFrame()
    
    def calculate_growth_rate(self, data: pd.DataFrame, keyword: str) -> float:
        """키워드의 성장률 계산"""
        try:
            if keyword not in data.columns or len(data) < 2:
                return 0.0
            
            # 최근 데이터와 과거 데이터 비교
            recent_avg = data[keyword].tail(7).mean()  # 최근 1주일
            past_avg = data[keyword].head(7).mean()    # 첫 1주일
            
            if past_avg > 0:
                growth_rate = ((recent_avg - past_avg) / past_avg) * 100
                return round(growth_rate, 2)
            return 0.0
            
        except Exception as e:
            self.logger.error(f"성장률 계산 오류: {e}")
            return 0.0
    
    def get_trend_direction(self, data: pd.DataFrame, keyword: str) -> str:
        """트렌드 방향 분석"""
        try:
            if keyword not in data.columns or len(data) < 7:
                return "insufficient_data"
            
            # 최근 데이터의 추세 분석
            recent_data = data[keyword].tail(14).values
            x = np.arange(len(recent_data))
            
            # 선형 회귀로 추세 계산
            coefficients = np.polyfit(x, recent_data, 1)
            slope = coefficients[0]
            
            if slope > 0.5:
                return "rising"
            elif slope < -0.5:
                return "falling"
            else:
                return "stable"
                
        except Exception as e:
            self.logger.error(f"트렌드 방향 분석 오류: {e}")
            return "unknown"
    
    def get_average_interest(self, data: pd.DataFrame, keyword: str) -> float:
        """평균 관심도 계산"""
        try:
            if keyword not in data.columns:
                return 0.0
            
            return round(data[keyword].mean(), 2)
            
        except Exception as e:
            self.logger.error(f"평균 관심도 계산 오류: {e}")
            return 0.0
    
    @lru_cache(maxsize=1000)
    def get_cached_trends(self, keyword_tuple: tuple) -> Optional[Dict[str, Any]]:
        """캐시된 트렌드 데이터 반환 (메모리 캐시)"""
        # 실제 구현에서는 데이터베이스 캐시 사용
        return None