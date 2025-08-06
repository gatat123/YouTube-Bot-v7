"""
YouTube 키워드 분석 봇 v7 - 설정 관리
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
import logging

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API 키 설정"""
    discord_token: str
    gemini_key: str  # Gemini가 주요 AI
    youtube_key: Optional[str]
    tiktok_key: Optional[str] = None  # TikTok API 키 (선택적)
    twitter_bearer: Optional[str] = None  # Twitter Bearer Token (선택적)
    
    # PostgreSQL 설정 (Railway)
    pg_host: Optional[str] = None
    pg_port: Optional[int] = None
    pg_database: Optional[str] = None
    pg_user: Optional[str] = None
    pg_password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """환경 변수에서 API 키 로드"""
        return cls(
            discord_token=os.getenv('DISCORD_BOT_TOKEN', ''),
            gemini_key=os.getenv('GEMINI_API_KEY', ''),
            youtube_key=os.getenv('YOUTUBE_API_KEY'),
            tiktok_key=os.getenv('TIKTOK_API_KEY'),
            twitter_bearer=os.getenv('TWITTER_BEARER_TOKEN'),
            # PostgreSQL (Railway 자동 제공)
            pg_host=os.getenv('PGHOST'),
            pg_port=int(os.getenv('PGPORT', 5432)) if os.getenv('PGPORT') else None,
            pg_database=os.getenv('PGDATABASE'),
            pg_user=os.getenv('PGUSER'),
            pg_password=os.getenv('PGPASSWORD')
        )
    
    def validate(self) -> List[str]:
        """필수 API 키 검증"""
        missing = []
        if not self.discord_token:
            missing.append('DISCORD_BOT_TOKEN')
        if not self.gemini_key:
            missing.append('GEMINI_API_KEY')
        return missing


@dataclass
class AnalysisConfig:
    """분석 설정"""
    # 키워드 확장 설정
    keyword_expansion: Dict = field(default_factory=lambda: {
        'core_keywords': 30,
        'search_intent': 20,
        'target_audience': 15,
        'temporal': 10,
        'long_tail': 15,
        'total_target': 90,
        'final_selection': 40
    })
    
    # 필터링 임계값
    filtering_thresholds: Dict = field(default_factory=lambda: {
        'min_search_volume': 100,
        'max_competition': 0.8,
        'min_trend_score': 30,
        'min_relevance': 0.5
    })
    
    # 트렌드 분석 설정
    trends_config: Dict = field(default_factory=lambda: {
        'timeframe': 'today 3-m',  # 최근 3개월
        'geo': 'KR',  # 한국
        'batch_size': 4,  # Google Trends 제한
        'cache_ttl': 7200  # 2시간
    })
    
    # YouTube API 설정
    youtube_config: Dict = field(default_factory=lambda: {
        'max_results': 50,
        'region_code': 'KR',
        'relevance_language': 'ko',
        'order': 'relevance'
    })


@dataclass
class CategoryConfig:
    """카테고리별 설정"""
    categories: Dict[str, Dict] = field(default_factory=lambda: {
        'Gaming': {
            'keywords': ['게임', '플레이', '공략', '가이드'],
            'boost_words': ['초보', '꿀팁', '최신'],
            'optimal_length': '10-20분',
            'upload_times': ['금요일 20:00', '토요일 15:00']
        },
        'Education': {
            'keywords': ['강의', '튜토리얼', '배우기', '공부'],
            'boost_words': ['쉽게', '기초', '완벽정리'],
            'optimal_length': '8-15분',
            'upload_times': ['평일 18:00-20:00']
        },
        'Entertainment': {
            'keywords': ['웃긴', '재미있는', '리액션', '몰카'],
            'boost_words': ['레전드', '역대급', '충격'],
            'optimal_length': '5-10분',
            'upload_times': ['매일 19:00-21:00']
        },
        'Tech': {
            'keywords': ['리뷰', '언박싱', '비교', '신제품'],
            'boost_words': ['2025', '최신', '비교분석'],
            'optimal_length': '8-12분',
            'upload_times': ['화요일, 목요일 19:00']
        },
        'Vlog': {
            'keywords': ['일상', '브이로그', '데일리', '루틴'],
            'boost_words': ['리얼', '소통', '공감'],
            'optimal_length': '10-15분',
            'upload_times': ['주말 14:00, 20:00']
        },
        'Food': {
            'keywords': ['레시피', '요리', '먹방', '맛집'],
            'boost_words': ['간단', '초간단', '꿀맛'],
            'optimal_length': '5-15분',
            'upload_times': ['점심시간', '저녁시간']
        }
    })
    
    def get_category(self, name: str) -> Dict:
        """카테고리 정보 가져오기"""
        return self.categories.get(name, self.categories.get('Entertainment', {}))


@dataclass
class BotConfig:
    """봇 전체 설정"""
    api: APIConfig
    analysis: AnalysisConfig
    categories: CategoryConfig
    
    # 봇 설정
    command_prefix: str = '/'
    embed_color: int = 0xFF0000  # YouTube Red
    
    # 성능 설정
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    cache_enabled: bool = True
    
    # Railway 배포 설정
    port: int = field(default_factory=lambda: int(os.getenv('PORT', 8080)))
    environment: str = field(default_factory=lambda: os.getenv('RAILWAY_ENVIRONMENT', 'development'))
    
    @classmethod
    def load(cls) -> 'BotConfig':
        """설정 로드"""
        api_config = APIConfig.from_env()
        
        # API 키 검증
        missing_keys = api_config.validate()
        if missing_keys:
            logger.warning(f"누락된 API 키: {', '.join(missing_keys)}")
        
        return cls(
            api=api_config,
            analysis=AnalysisConfig(),
            categories=CategoryConfig()
        )
    
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.environment == 'production'


# 전역 설정 인스턴스
config = BotConfig.load()

# 설정 정보 출력
logger.info(f"봇 설정 로드 완료")
logger.info(f"환경: {config.environment}")
logger.info(f"포트: {config.port}")
logger.info(f"캐시: {'활성화' if config.cache_enabled else '비활성화'}")
logger.info(f"PostgreSQL: {'연결됨' if config.api.pg_host else '미연결 (메모리 캐시만 사용)'}")