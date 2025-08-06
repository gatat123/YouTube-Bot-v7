"""
API 관리자 - 통합 API 호출 및 Rate Limiting
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class APIRateLimiter:
    """API Rate Limiter"""
    calls_per_minute: int
    _call_times: List[datetime] = None
    
    def __post_init__(self):
        self._call_times = []
    
    async def check_rate_limit(self, api_name: str):
        """Rate limit 체크 및 대기"""
        now = datetime.now()
        
        # 1분 이전 호출 제거
        self._call_times = [
            call_time for call_time in self._call_times 
            if now - call_time < timedelta(minutes=1)
        ]
        
        # Rate limit 확인
        if len(self._call_times) >= self.calls_per_minute:
            # 가장 오래된 호출로부터 1분 대기
            oldest_call = min(self._call_times)
            wait_time = 60 - (now - oldest_call).total_seconds()
            
            if wait_time > 0:
                logger.info(f"{api_name} rate limit 대기: {wait_time:.1f}초")
                await asyncio.sleep(wait_time)
        
        # 호출 시간 기록
        self._call_times.append(now)


class APIManager:
    """통합 API 관리자"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API별 Rate Limiter
        self.rate_limiters = {
            'youtube': APIRateLimiter(100),          # 100 calls/min
            'claude': APIRateLimiter(50),             # 50 calls/min
            'gemini': APIRateLimiter(60),             # 60 calls/min
            'twitter': APIRateLimiter(180),           # 180 calls/min
            'tiktok': APIRateLimiter(100),            # 100 calls/min
        }
        
        # API 통계
        self.stats = defaultdict(lambda: {
            'calls': 0,
            'errors': 0,
            'total_time': 0
        })
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def make_request(self, 
                          api_name: str,
                          method: str,
                          url: str,
                          **kwargs) -> Dict[str, Any]:
        """통합 API 요청 처리"""
        # Rate limit 체크
        rate_limiter = self.rate_limiters.get(api_name)
        if rate_limiter:
            await rate_limiter.check_rate_limit(api_name)
        
        start_time = datetime.now()
        
        try:
            if not self.session:
                raise RuntimeError("APIManager session not initialized")
            
            async with self.session.request(method, url, **kwargs) as response:
                # 통계 업데이트
                elapsed = (datetime.now() - start_time).total_seconds()
                self.stats[api_name]['calls'] += 1
                self.stats[api_name]['total_time'] += elapsed
                
                # 응답 처리
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limit
                    retry_after = response.headers.get('Retry-After', 60)
                    logger.warning(f"{api_name} rate limit 응답. {retry_after}초 대기")
                    await asyncio.sleep(int(retry_after))
                    raise aiohttp.ClientError("Rate limited")
                else:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"API error {response.status}: {error_text}")
                    
        except Exception as e:
            self.stats[api_name]['errors'] += 1
            logger.error(f"{api_name} API 오류: {e}")
            raise
    
    async def batch_request(self,
                           api_name: str,
                           requests: List[Dict[str, Any]],
                           batch_size: int = 5,
                           delay: float = 0.5) -> List[Any]:
        """배치 API 요청 처리"""
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i+batch_size]
            
            # 병렬 요청
            tasks = [
                self.make_request(api_name, **req)
                for req in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # 배치 간 딜레이
            if i + batch_size < len(requests):
                await asyncio.sleep(delay)
        
        return results
    
    def get_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """API 사용 통계 조회"""
        if api_name:
            stats = self.stats[api_name]
            avg_time = stats['total_time'] / stats['calls'] if stats['calls'] > 0 else 0
            
            return {
                'api': api_name,
                'total_calls': stats['calls'],
                'total_errors': stats['errors'],
                'error_rate': f"{(stats['errors'] / stats['calls'] * 100):.1f}%" if stats['calls'] > 0 else "0%",
                'avg_response_time': f"{avg_time:.3f}s"
            }
        else:
            # 전체 통계
            all_stats = {}
            for api in self.stats:
                all_stats[api] = self.get_stats(api)
            return all_stats


class ParallelAPIExecutor:
    """병렬 API 실행 관리"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
    
    async def execute(self, tasks: List[Callable], progress_callback: Optional[Callable] = None) -> List[Any]:
        """병렬로 여러 작업 실행"""
        results = []
        completed = 0
        
        async def run_with_semaphore(task, index):
            async with self.semaphore:
                try:
                    result = await task()
                    
                    nonlocal completed
                    completed += 1
                    
                    if progress_callback:
                        await progress_callback(completed, len(tasks))
                    
                    return index, result
                except Exception as e:
                    logger.error(f"작업 {index} 실행 오류: {e}")
                    return index, None
        
        # 모든 작업을 병렬로 실행
        coroutines = [
            run_with_semaphore(task, i)
            for i, task in enumerate(tasks)
        ]
        
        # 결과 수집 및 순서 유지
        results_with_index = await asyncio.gather(*coroutines)
        
        # 원래 순서대로 정렬
        results_with_index.sort(key=lambda x: x[0])
        
        return [result for _, result in results_with_index]


# 싱글톤 인스턴스
api_manager = APIManager()
