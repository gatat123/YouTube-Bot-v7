"""
캐시 매니저 - Python 메모리 캐싱 (PostgreSQL 백업)
"""

import asyncio
import json
import hashlib
import time
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime, timedelta
import logging
from cachetools import TTLCache, LRUCache
import asyncpg
import os
from dataclasses import dataclass, asdict
from dataclasses_json import dataclass_json
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class CacheEntry:
    """캐시 엔트리 데이터 클래스"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hit_count: int = 0
    category: str = "general"


class CacheManager:
    """Python 메모리 기반 캐시 매니저 (PostgreSQL 백업)"""
    
    def __init__(self):
        # 메모리 캐시 초기화
        self.memory_cache = TTLCache(maxsize=1000, ttl=3600)  # 기본 1시간 TTL
        self.lru_cache = LRUCache(maxsize=500)  # LRU 캐시 (자주 사용되는 항목)
        
        # 동적 TTL 전략
        self.ttl_strategy = {
            "trending": 1800,      # 30분 - 급상승 키워드
            "stable": 86400,       # 24시간 - 안정적 키워드
            "seasonal": 604800,    # 7일 - 계절성 키워드
            "competitor": 43200,   # 12시간 - 경쟁자 분석
            "general": 3600        # 1시간 - 일반
        }
        
        # PostgreSQL 연결 정보 (Railway 환경변수)
        self.db_config = {
            'host': os.getenv('PGHOST', 'localhost'),
            'port': os.getenv('PGPORT', 5432),
            'database': os.getenv('PGDATABASE', 'railway'),
            'user': os.getenv('PGUSER', 'postgres'),
            'password': os.getenv('PGPASSWORD', '')
        }
        
        self.db_pool = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "db_saves": 0,
            "db_loads": 0
        }
        
        logger.info("캐시 매니저 초기화 완료")
    
    async def initialize(self):
        """PostgreSQL 연결 및 테이블 초기화"""
        try:
            if self.db_config['password']:  # PostgreSQL이 설정된 경우에만
                self.db_pool = await asyncpg.create_pool(**self.db_config)
                await self._create_cache_table()
                logger.info("PostgreSQL 백업 스토리지 연결 완료")
            else:
                logger.info("PostgreSQL 설정 없음 - 메모리 캐시만 사용")
        except Exception as e:
            logger.warning(f"PostgreSQL 연결 실패, 메모리 캐시만 사용: {e}")
            self.db_pool = None
    
    async def _create_cache_table(self):
        """캐시 테이블 생성"""
        if not self.db_pool:
            return
            
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value JSONB,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    hit_count INTEGER DEFAULT 0,
                    category TEXT
                )
            ''')
            
            # 인덱스 생성
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_cache_expires 
                ON cache_entries(expires_at)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_cache_category 
                ON cache_entries(category)
            ''')
    
    def _generate_key(self, prefix: str, params: Union[str, Dict]) -> str:
        """캐시 키 생성"""
        if isinstance(params, dict):
            params_str = json.dumps(params, sort_keys=True)
        else:
            params_str = str(params)
        
        hash_digest = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_digest}"
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        # 1. 메모리 캐시 확인
        if key in self.memory_cache:
            self.stats["hits"] += 1
            entry = self.memory_cache[key]
            if isinstance(entry, CacheEntry):
                entry.hit_count += 1
                # 자주 사용되는 항목은 LRU 캐시에도 저장
                if entry.hit_count > 3:
                    self.lru_cache[key] = entry
                return entry.value
            return entry
        
        # 2. LRU 캐시 확인
        if key in self.lru_cache:
            self.stats["hits"] += 1
            entry = self.lru_cache[key]
            if isinstance(entry, CacheEntry):
                if entry.expires_at > time.time():
                    return entry.value
                else:
                    del self.lru_cache[key]
        
        # 3. PostgreSQL에서 조회 (백업)
        if self.db_pool:
            try:
                value = await self._get_from_db(key)
                if value is not None:
                    self.stats["db_loads"] += 1
                    # 메모리 캐시에 복원
                    self.memory_cache[key] = value
                    return value.value if isinstance(value, CacheEntry) else value
            except Exception as e:
                logger.error(f"DB 조회 실패: {e}")
        
        self.stats["misses"] += 1
        return None
    
    async def _get_from_db(self, key: str) -> Optional[CacheEntry]:
        """PostgreSQL에서 캐시 조회"""
        if not self.db_pool:
            return None
            
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT value, created_at, expires_at, hit_count, category
                FROM cache_entries
                WHERE key = $1 AND expires_at > NOW()
            ''', key)
            
            if row:
                # hit_count 증가
                await conn.execute('''
                    UPDATE cache_entries 
                    SET hit_count = hit_count + 1 
                    WHERE key = $1
                ''', key)
                
                return CacheEntry(
                    key=key,
                    value=json.loads(row['value']),
                    created_at=row['created_at'].timestamp(),
                    expires_at=row['expires_at'].timestamp(),
                    hit_count=row['hit_count'],
                    category=row['category']
                )
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  category: str = "general") -> bool:
        """캐시에 값 저장"""
        try:
            # TTL 결정
            if ttl is None:
                ttl = self.ttl_strategy.get(category, 3600)
            
            # 캐시 엔트리 생성
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=time.time() + ttl,
                hit_count=0,
                category=category
            )
            
            # 메모리 캐시에 저장
            self.memory_cache[key] = entry
            
            # PostgreSQL에 비동기 저장 (백업)
            if self.db_pool:
                asyncio.create_task(self._save_to_db(entry))
            
            return True
            
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
            return False
    
    async def _save_to_db(self, entry: CacheEntry):
        """PostgreSQL에 캐시 저장"""
        if not self.db_pool:
            return
            
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO cache_entries (key, value, created_at, expires_at, hit_count, category)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (key) DO UPDATE
                    SET value = $2, expires_at = $4, hit_count = cache_entries.hit_count + 1
                ''', 
                entry.key, 
                json.dumps(entry.value),
                datetime.fromtimestamp(entry.created_at),
                datetime.fromtimestamp(entry.expires_at),
                entry.hit_count,
                entry.category
                )
                self.stats["db_saves"] += 1
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            # 메모리 캐시에서 삭제
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.lru_cache:
                del self.lru_cache[key]
            
            # PostgreSQL에서 삭제
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.execute('DELETE FROM cache_entries WHERE key = $1', key)
            
            return True
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")
            return False
    
    async def clear_expired(self):
        """만료된 캐시 정리"""
        # 메모리 캐시는 TTLCache가 자동 처리
        
        # PostgreSQL 정리
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    deleted = await conn.execute('''
                        DELETE FROM cache_entries 
                        WHERE expires_at < NOW()
                    ''')
                    logger.info(f"만료된 캐시 {deleted} 개 삭제")
            except Exception as e:
                logger.error(f"만료 캐시 정리 실패: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "memory_cache_size": len(self.memory_cache),
            "lru_cache_size": len(self.lru_cache),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "db_saves": self.stats["db_saves"],
            "db_loads": self.stats["db_loads"]
        }
    
    def cache_keywords(self, prefix: str, ttl: Optional[int] = None, 
                      category: str = "general") -> Callable:
        """키워드 캐싱 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 캐시 키 생성
                cache_key = self._generate_key(prefix, {
                    'args': str(args[1:]),  # self는 제외
                    'kwargs': kwargs
                })
                
                # 캐시에서 조회
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"캐시 히트: {cache_key}")
                    return cached_result
                
                # 함수 실행
                logger.debug(f"캐시 미스: {cache_key}, 함수 실행 중")
                result = await func(*args, **kwargs)
                
                # 결과 캐싱
                await self.set(cache_key, result, ttl=ttl, category=category)
                
                return result
            return wrapper
        return decorator
    
    async def close(self):
        """리소스 정리"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("PostgreSQL 연결 종료")


# 싱글톤 인스턴스
cache_manager = CacheManager()