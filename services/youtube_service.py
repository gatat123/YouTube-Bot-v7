"""
YouTube Data API v3 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import numpy as np
import logging
import asyncio
from urllib.parse import quote

from config import config
from utils import cache_manager

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube API 서비스"""
    
    def __init__(self):
        self.api_key = config.api.youtube_key
        self.youtube = None
        
        if self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("✅ YouTube API 초기화 성공")
            except Exception as e:
                logger.error(f"YouTube API 초기화 실패: {e}")
    
    @cache_manager.cache_keywords("youtube_metrics", ttl=3600)
    async def get_comprehensive_metrics(self, keyword: str) -> Dict[str, Any]:
        """종합적인 YouTube 메트릭 수집"""
        if not self.youtube:
            return self._get_default_metrics()
        
        try:
            # 병렬로 여러 시간대 분석
            time_ranges = [
                ('24h', 1),
                ('7d', 7),
                ('30d', 30)
            ]
            
            tasks = []
            for label, days in time_ranges:
                task = self._analyze_time_range(keyword, label, days)
                tasks.append(task)
            
            # 모든 시간대 분석 완료
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 통합
            metrics = {
                'upload_frequency': {},
                'view_velocity': {},
                'engagement_metrics': {},
                'channel_diversity': {},
                'content_quality': {}
            }
            
            for i, (label, _) in enumerate(time_ranges):
                if isinstance(results[i], Exception):
                    logger.error(f"시간대 분석 오류 ({label}): {results[i]}")
                    continue
                
                result = results[i]
                metrics['upload_frequency'][label] = result.get('upload_count', 0)
                metrics['view_velocity'][label] = result.get('view_velocity', {})
                metrics['engagement_metrics'][label] = result.get('engagement', {})
                metrics['channel_diversity'][label] = result.get('channel_diversity', 0)
            
            # 경쟁도 및 기회 점수 계산
            competition = self._calculate_competition(metrics)
            opportunity = self._calculate_opportunity(metrics, competition)
            
            # 콘텐츠 품질 분석
            quality_score = await self._analyze_content_quality(keyword)
            
            return {
                **metrics,
                'competition': competition,
                'opportunity': opportunity,
                'quality_score': quality_score,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"YouTube 메트릭 수집 오류: {e}")
            return self._get_default_metrics()
    
    async def _analyze_time_range(self, keyword: str, label: str, days: int) -> Dict[str, Any]:
        """특정 시간대 분석"""
        try:
            # 비동기 실행을 위한 래퍼
            loop = asyncio.get_event_loop()
            
            # 검색 실행
            published_after = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
            
            search_response = await loop.run_in_executor(
                None,
                lambda: self.youtube.search().list(
                    q=keyword,
                    part='id,snippet',
                    type='video',
                    order='date',
                    publishedAfter=published_after,
                    maxResults=50,
                    regionCode='KR'
                ).execute()
            )
            
            items = search_response.get('items', [])
            upload_count = len(items)
            
            if not items:
                return {
                    'upload_count': 0,
                    'view_velocity': {'avg': 0, 'median': 0, 'max': 0},
                    'engagement': {'avg_rate': 0, 'high_ratio': 0},
                    'channel_diversity': 0
                }
            
            # 비디오 상세 정보 가져오기
            video_ids = [item['id']['videoId'] for item in items[:20]]
            
            videos_response = await loop.run_in_executor(
                None,
                lambda: self.youtube.videos().list(
                    part='statistics,snippet,contentDetails',
                    id=','.join(video_ids)
                ).execute()
            )
            
            # 메트릭 계산
            view_velocities = []
            engagement_rates = []
            unique_channels = set()
            
            for video in videos_response.get('items', []):
                stats = video['statistics']
                snippet = video['snippet']
                
                # 채널 다양성
                unique_channels.add(snippet['channelId'])
                
                # 조회수 속도
                published = datetime.fromisoformat(
                    snippet['publishedAt'].replace('Z', '+00:00')
                )
                hours_since = (datetime.now(timezone.utc) - published).total_seconds() / 3600
                
                views = int(stats.get('viewCount', 0))
                if hours_since > 0:
                    velocity = views / hours_since
                    view_velocities.append(velocity)
                
                # 참여율
                if views > 0:
                    likes = int(stats.get('likeCount', 0))
                    comments = int(stats.get('commentCount', 0))
                    engagement = (likes + comments) / views * 100
                    engagement_rates.append(engagement)
            
            # 통계 계산
            return {
                'upload_count': upload_count,
                'view_velocity': {
                    'avg': np.mean(view_velocities) if view_velocities else 0,
                    'median': np.median(view_velocities) if view_velocities else 0,
                    'max': max(view_velocities) if view_velocities else 0,
                    'p75': np.percentile(view_velocities, 75) if view_velocities else 0
                },
                'engagement': {
                    'avg_rate': np.mean(engagement_rates) if engagement_rates else 0,
                    'high_ratio': len([e for e in engagement_rates if e > 5]) / len(engagement_rates) if engagement_rates else 0,
                    'median_rate': np.median(engagement_rates) if engagement_rates else 0
                },
                'channel_diversity': len(unique_channels) / len(items) if items else 0
            }
            
        except Exception as e:
            logger.error(f"시간대 분석 오류: {e}")
            return {
                'upload_count': 0,
                'view_velocity': {'avg': 0, 'median': 0, 'max': 0},
                'engagement': {'avg_rate': 0, 'high_ratio': 0},
                'channel_diversity': 0
            }
    
    async def get_channel_details(self, channel_ids: List[str]) -> Dict[str, Any]:
        """채널 상세 정보 조회"""
        if not self.youtube or not channel_ids:
            return {}
        
        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.youtube.channels().list(
                    part='statistics,snippet,brandingSettings',
                    id=','.join(channel_ids[:50])
                ).execute()
            )
            
            channels = {}
            for channel in response.get('items', []):
                channel_id = channel['id']
                stats = channel['statistics']
                snippet = channel['snippet']
                
                channels[channel_id] = {
                    'title': snippet['title'],
                    'subscriber_count': int(stats.get('subscriberCount', 0)),
                    'view_count': int(stats.get('viewCount', 0)),
                    'video_count': int(stats.get('videoCount', 0)),
                    'description': snippet.get('description', ''),
                    'country': snippet.get('country', 'unknown')
                }
            
            return channels
            
        except Exception as e:
            logger.error(f"채널 정보 조회 오류: {e}")
            return {}
    
    async def get_video_suggestions(self, keyword: str) -> List[str]:
        """YouTube 자동완성 제안"""
        try:
            # YouTube 자동완성 API (비공식)
            url = f"http://suggestqueries.google.com/complete/search"
            params = {
                'client': 'youtube',
                'ds': 'yt',
                'q': keyword,
                'hl': 'ko',
                'gl': 'kr'
            }
            
            # aiohttp로 요청
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        text = await response.text()
                        
                        # JSONP 파싱
                        if text.startswith('window.google.ac.h('):
                            import json
                            json_text = text[19:-1]
                            data = json.loads(json_text)
                            
                            suggestions = []
                            if len(data) > 1 and isinstance(data[1], list):
                                for item in data[1]:
                                    if isinstance(item, list) and len(item) > 0:
                                        suggestions.append(item[0])
                                    else:
                                        suggestions.append(str(item))
                            
                            return suggestions[:20]
        
        except Exception as e:
            logger.error(f"자동완성 제안 오류: {e}")
        
        return []
    
    async def _analyze_content_quality(self, keyword: str) -> float:
        """콘텐츠 품질 분석"""
        try:
            loop = asyncio.get_event_loop()
            
            # 최근 인기 동영상 분석
            search_response = await loop.run_in_executor(
                None,
                lambda: self.youtube.search().list(
                    q=keyword,
                    part='id',
                    type='video',
                    order='viewCount',
                    maxResults=10,
                    regionCode='KR'
                ).execute()
            )
            
            if not search_response.get('items'):
                return 50.0
            
            video_ids = [item['id']['videoId'] for item in search_response['items']]
            
            # 비디오 상세 정보
            videos_response = await loop.run_in_executor(
                None,
                lambda: self.youtube.videos().list(
                    part='contentDetails,statistics',
                    id=','.join(video_ids)
                ).execute()
            )
            
            quality_scores = []
            
            for video in videos_response.get('items', []):
                stats = video['statistics']
                details = video['contentDetails']
                
                # 품질 지표
                views = int(stats.get('viewCount', 0))
                likes = int(stats.get('likeCount', 0))
                
                if views > 0:
                    # 좋아요 비율
                    like_ratio = likes / views * 100
                    
                    # 동영상 길이 (적정 길이 보너스)
                    duration = self._parse_duration(details['duration'])
                    duration_score = 100 if 300 <= duration <= 900 else 70  # 5-15분 최적
                    
                    # 품질 점수 계산
                    quality = (like_ratio * 10 + duration_score) / 2
                    quality_scores.append(min(100, quality))
            
            return np.mean(quality_scores) if quality_scores else 50.0
            
        except Exception as e:
            logger.error(f"콘텐츠 품질 분석 오류: {e}")
            return 50.0
    
    def _parse_duration(self, duration_str: str) -> int:
        """ISO 8601 duration을 초로 변환"""
        import re
        
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _calculate_competition(self, metrics: Dict[str, Any]) -> str:
        """경쟁도 계산"""
        daily_uploads = metrics['upload_frequency'].get('24h', 0)
        weekly_uploads = metrics['upload_frequency'].get('7d', 0)
        channel_diversity = metrics['channel_diversity'].get('7d', 0)
        
        # 점수 기반 경쟁도
        competition_score = 0
        
        # 업로드 빈도
        if daily_uploads >= 20:
            competition_score += 3
        elif daily_uploads >= 10:
            competition_score += 2
        elif daily_uploads >= 5:
            competition_score += 1
        
        # 주간 업로드
        if weekly_uploads >= 200:
            competition_score += 3
        elif weekly_uploads >= 100:
            competition_score += 2
        elif weekly_uploads >= 50:
            competition_score += 1
        
        # 채널 다양성 (낮을수록 독점적)
        if channel_diversity < 0.3:
            competition_score += 2
        elif channel_diversity < 0.5:
            competition_score += 1
        
        # 최종 경쟁도
        if competition_score >= 6:
            return 'high'
        elif competition_score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_opportunity(self, metrics: Dict[str, Any], competition: str) -> float:
        """기회 점수 계산 (0-100)"""
        score = 0
        
        # 경쟁도 기반 점수
        competition_scores = {'low': 40, 'medium': 25, 'high': 10}
        score += competition_scores.get(competition, 20)
        
        # 조회수 속도
        avg_velocity = metrics['view_velocity'].get('7d', {}).get('avg', 0)
        if avg_velocity > 5000:  # 시간당 5000뷰 이상
            score += 30
        elif avg_velocity > 1000:
            score += 20
        elif avg_velocity > 100:
            score += 10
        
        # 참여율
        engagement = metrics['engagement_metrics'].get('7d', {}).get('avg_rate', 0)
        if engagement > 8:  # 8% 이상
            score += 30
        elif engagement > 5:
            score += 20
        elif engagement > 2:
            score += 10
        
        return min(100, score)
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """기본 메트릭"""
        return {
            'upload_frequency': {'24h': 0, '7d': 0, '30d': 0},
            'view_velocity': {
                '24h': {'avg': 0, 'median': 0, 'max': 0},
                '7d': {'avg': 0, 'median': 0, 'max': 0},
                '30d': {'avg': 0, 'median': 0, 'max': 0}
            },
            'engagement_metrics': {
                '24h': {'avg_rate': 0, 'high_ratio': 0},
                '7d': {'avg_rate': 0, 'high_ratio': 0},
                '30d': {'avg_rate': 0, 'high_ratio': 0}
            },
            'channel_diversity': {'24h': 0, '7d': 0, '30d': 0},
            'competition': 'unknown',
            'opportunity': 50,
            'quality_score': 50,
            'analyzed_at': datetime.now().isoformat()
        }
