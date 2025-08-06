# services/trends_service.py - 한국 지역 전용, 가짜 데이터 없음

import logging
import time
import random
from typing import Dict, List, Optional, Union
from pytrends.request import TrendReq
import pandas as pd
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
import ssl

logger = logging.getLogger(__name__)

class TrendsService:
    """Google Trends API 서비스 (한국 전용 강력 우회)"""
    
    def __init__(self):
        self.pytrends = None
        self.last_request_time = 0
        self.request_count = 0
        self.session_pool = []  # 여러 세션 관리
        self.current_session_idx = 0
        self._init_session_pool()
        
    def _create_session(self, session_id: int):
        """강화된 세션 생성"""
        session = requests.Session()
        
        # SSL 컨텍스트 커스터마이징
        class CustomAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = create_urllib3_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = context
                return super().init_poolmanager(*args, **kwargs)
        
        # urllib3 버전 호환성
        try:
            retries = Retry(
                total=10,  # 재시도 횟수 증가
                backoff_factor=1.0,  # 백오프 팩터 증가
                status_forcelist=[429, 500, 502, 503, 504, 403],
                allowed_methods=["GET", "POST", "HEAD", "OPTIONS"]
            )
        except TypeError:
            retries = Retry(
                total=10,
                backoff_factor=1.0,
                status_forcelist=[429, 500, 502, 503, 504, 403],
                method_whitelist=["GET", "POST", "HEAD", "OPTIONS"]
            )
            
        adapter = CustomAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # 다양한 User-Agent 풀
        user_agents = [
            # Chrome Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Chrome Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            # Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            # Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        
        # 세션별 다른 헤더 설정
        headers = {
            'User-Agent': user_agents[session_id % len(user_agents)],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
            'DNT': '1'
        }
        
        # 리퍼러 추가 (구글 검색에서 온 것처럼)
        if session_id % 3 == 0:
            headers['Referer'] = 'https://www.google.com/'
        elif session_id % 3 == 1:
            headers['Referer'] = 'https://www.google.co.kr/'
        
        session.headers.update(headers)
        
        # 쿠키 설정 (구글 세션처럼 보이게)
        session.cookies.set('NID', f'511=fake_nid_{random.randint(1000000, 9999999)}', domain='.google.com')
        session.cookies.set('1P_JAR', f'2024-{random.randint(1,12)}-{random.randint(1,28)}', domain='.google.com')
        
        return session
        
    def _init_session_pool(self):
        """세션 풀 초기화 (5개 세션 관리)"""
        self.session_pool = []
        for i in range(5):
            session = self._create_session(i)
            self.session_pool.append(session)
            logger.info(f"세션 {i+1}/5 생성 완료")
            
    def _get_next_session(self):
        """라운드 로빈 방식으로 세션 선택"""
        session = self.session_pool[self.current_session_idx]
        self.current_session_idx = (self.current_session_idx + 1) % len(self.session_pool)
        return session
            
    def _init_pytrends_with_session(self, session):
        """특정 세션으로 pytrends 초기화"""
        try:
            # 한국 설정으로만 시도
            self.pytrends = TrendReq(
                hl='ko',  # 한국어
                tz=540,   # KST (UTC+9)
                geo='KR',  # 한국
                timeout=(30, 60),  # 연결 타임아웃 30초, 읽기 타임아웃 60초
                retries=5,
                backoff_factor=2.0
            )
            
            # 세션 교체
            self.pytrends.requests = session
            
            # 프록시 설정 (옵션)
            # self.pytrends.proxies = {
            #     'http': 'http://proxy.example.com:8080',
            #     'https': 'https://proxy.example.com:8080'
            # }
            
            logger.info("✅ pytrends 초기화 성공 (KR 전용)")
            return True
            
        except Exception as e:
            logger.error(f"pytrends 초기화 실패: {e}")
            return False
            
    def _aggressive_wait(self):
        """공격적인 대기 전략"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 요청 횟수에 따른 점진적 대기 시간 증가
        if self.request_count < 5:
            base_wait = random.uniform(5, 10)  # 5-10초
        elif self.request_count < 10:
            base_wait = random.uniform(15, 30)  # 15-30초
        elif self.request_count < 20:
            base_wait = random.uniform(30, 60)  # 30-60초
        else:
            base_wait = random.uniform(60, 120)  # 1-2분
            
        # 추가 랜덤 요소
        jitter = random.uniform(0, base_wait * 0.2)
        total_wait = base_wait + jitter
        
        if time_since_last < total_wait:
            sleep_time = total_wait - time_since_last
            logger.info(f"⏳ 대기 중... {sleep_time:.1f}초 (요청 #{self.request_count + 1})")
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        self.request_count += 1
        
    def get_interest_over_time(self, keywords: List[str], timeframe: str = 'today 3-m') -> Optional[pd.DataFrame]:
        """트렌드 데이터 가져오기 (실패시 None 반환)"""
        # 키워드 검증
        keywords = [k.strip() for k in keywords if k and k.strip()][:5]
        
        if not keywords:
            logger.error("유효한 키워드가 없습니다")
            return None
            
        # 최대 재시도 횟수
        max_attempts = 10
        
        for attempt in range(max_attempts):
            try:
                # 대기
                self._aggressive_wait()
                
                # 세션 선택
                session = self._get_next_session()
                
                # pytrends 재초기화
                if not self._init_pytrends_with_session(session):
                    continue
                    
                logger.info(f"🔍 Google Trends 요청 시도 {attempt + 1}/{max_attempts}: {keywords}")
                
                # 페이로드 빌드
                self.pytrends.build_payload(
                    keywords, 
                    cat=0,
                    timeframe=timeframe,
                    geo='KR',  # 한국 고정
                    gprop=''
                )
                
                # 데이터 요청
                data = self.pytrends.interest_over_time()
                
                if data is not None and not data.empty:
                    logger.info(f"✅ 데이터 획득 성공! (시도 {attempt + 1})")
                    # isPartial 컬럼 제거
                    if 'isPartial' in data.columns:
                        data = data.drop('isPartial', axis=1)
                    return data
                else:
                    logger.warning(f"❌ 빈 데이터 (시도 {attempt + 1})")
                    
            except requests.exceptions.TooManyRedirects:
                logger.error(f"리다이렉트 과다 (시도 {attempt + 1})")
                time.sleep(random.uniform(30, 60))
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.error(f"⚠️ Rate limit! 긴 대기... (시도 {attempt + 1})")
                    time.sleep(random.uniform(300, 600))  # 5-10분 대기
                else:
                    logger.error(f"HTTP 에러: {e} (시도 {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"예외 발생: {e} (시도 {attempt + 1})")
                
            # 실패 후 추가 대기
            if attempt < max_attempts - 1:
                wait_time = random.uniform(30, 90) * (attempt + 1)
                logger.info(f"⏳ 재시도 전 대기: {wait_time:.1f}초")
                time.sleep(wait_time)
                
        # 모든 시도 실패
        logger.error(f"❌ Google Trends 데이터 획득 완전 실패 (총 {max_attempts}회 시도)")
        return None
        
    def get_related_queries(self, keyword: str) -> Optional[Dict]:
        """관련 검색어 가져오기"""
        try:
            self._aggressive_wait()
            
            session = self._get_next_session()
            self._init_pytrends_with_session(session)
            
            self.pytrends.build_payload([keyword], geo='KR')
            related = self.pytrends.related_queries()
            
            return related.get(keyword, {})
            
        except Exception as e:
            logger.error(f"관련 검색어 획득 실패: {e}")
            return None
            
    def get_trending_searches(self) -> Optional[pd.DataFrame]:
        """한국 실시간 인기 검색어"""
        try:
            self._aggressive_wait()
            
            session = self._get_next_session()
            self._init_pytrends_with_session(session)
            
            trending = self.pytrends.trending_searches(pn='south_korea')
            return trending
            
        except Exception as e:
            logger.error(f"실시간 검색어 획득 실패: {e}")
            return None