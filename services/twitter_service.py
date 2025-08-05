"""
Twitter 트렌드 모니터링 서비스 (스텁)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)


class TwitterService:
    """Twitter API v2 서비스 (향후 구현)"""
    
    def __init__(self):
        self.bearer_token = config.api.twitter_bearer
        
        if not self.bearer_token:
            logger.warning("Twitter Bearer Token 없음 - 기능 비활성화")
    
    async def get_trending_topics(self, location_id: str = "23424868") -> List[Dict[str, Any]]:
        """트렌딩 토픽 조회 (스텁)"""
        # location_id: 23424868 = South Korea
        # TODO: Twitter API v2 구현
        logger.info("Twitter 트렌딩 토픽 조회 - 향후 구현")
        
        return [
            {
                'topic': '#placeholder',
                'tweet_volume': 0,
                'trend': 'stable',
                'timestamp': datetime.now().isoformat()
            }
        ]
    
    async def search_tweets(self, query: str, count: int = 100) -> List[Dict[str, Any]]:
        """트윗 검색 (스텁)"""
        # TODO: Twitter API v2 구현
        logger.info(f"Twitter 검색: {query} - 향후 구현")
        
        return []
    
    async def analyze_sentiment(self, keyword: str) -> Dict[str, Any]:
        """감성 분석 (스텁)"""
        # TODO: 감성 분석 구현
        
        return {
            'keyword': keyword,
            'positive_ratio': 0.5,
            'negative_ratio': 0.3,
            'neutral_ratio': 0.2,
            'buzz_score': 50,
            'timestamp': datetime.now().isoformat()
        }