"""
경쟁자 분석 모듈 - YouTube 상위 채널 분석
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
import logging

from services import YouTubeService
from utils import cache_manager

logger = logging.getLogger(__name__)


class CompetitorAnalyzer:
    """YouTube 경쟁 채널 및 콘텐츠 분석"""
    
    def __init__(self):
        self.youtube = YouTubeService()
        logger.info("경쟁자 분석기 초기화")
    
    async def analyze_competition(self, 
                                 keyword: str,
                                 depth: int = 10) -> Dict[str, Any]:
        """
        키워드 경쟁 상황 종합 분석
        
        Args:
            keyword: 분석할 키워드
            depth: 분석할 상위 채널 수
            
        Returns:
            경쟁 분석 결과
        """
        try:
            # 캐시 확인
            cache_key = f"competition:{keyword}:{depth}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"경쟁 분석 캐시 히트: {keyword}")
                return cached_result
            
            # 병렬 분석 작업
            tasks = [
                self._analyze_top_channels(keyword, depth),
                self._analyze_content_gaps(keyword, []),  # 채널 정보는 나중에 전달
                self._analyze_upload_patterns([]),
                self._analyze_competitive_landscape([])
            ]
            
            # 첫 번째 작업 완료 대기 (채널 정보 필요)
            top_channels = await tasks[0]
            
            # 나머지 분석 수행
            content_gaps = await self._analyze_content_gaps(keyword, top_channels)
            upload_patterns = self._analyze_upload_patterns(top_channels)
            collab_opportunities = self._analyze_collaboration_opportunities(top_channels)
            landscape = self._analyze_competitive_landscape(top_channels)
            
            # 결과 통합
            result = {
                'keyword': keyword,
                'analyzed_at': datetime.now().isoformat(),
                'top_channels': top_channels,
                'content_gaps': content_gaps,
                'upload_patterns': upload_patterns,
                'collaboration_opportunities': collab_opportunities,
                'competitive_landscape': landscape,
                'summary': self._generate_competition_summary(
                    top_channels, content_gaps, landscape
                )
            }
            
            # 캐시 저장
            await cache_manager.set(cache_key, result, ttl=43200, category='competitor')
            
            return result
            
        except Exception as e:
            logger.error(f"경쟁 분석 오류: {e}")
            return {
                'keyword': keyword,
                'error': str(e),
                'top_channels': [],
                'content_gaps': [],
                'competitive_landscape': {'market_saturation': 'unknown'}
            }
    
    async def _analyze_top_channels(self, keyword: str, depth: int) -> List[Dict[str, Any]]:
        """상위 채널 분석"""
        if not self.youtube.youtube:
            return []
        
        try:
            # 키워드로 상위 영상 검색
            search_response = self.youtube.youtube.search().list(
                q=keyword,
                part='id,snippet',
                type='video',
                order='viewCount',
                maxResults=depth * 3,  # 여러 채널 확보를 위해 더 많이 검색
                regionCode='KR'
            ).execute()
            
            # 채널별 영상 그룹화
            channel_videos = {}
            for item in search_response.get('items', []):
                channel_id = item['snippet']['channelId']
                channel_title = item['snippet']['channelTitle']
                
                if channel_id not in channel_videos:
                    channel_videos[channel_id] = {
                        'channel_id': channel_id,
                        'channel_title': channel_title,
                        'videos': []
                    }
                
                channel_videos[channel_id]['videos'].append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'published_at': item['snippet']['publishedAt']
                })
            
            # 상위 채널 선택
            top_channel_ids = list(channel_videos.keys())[:depth]
            
            # 채널 상세 정보 가져오기
            channel_details = await self.youtube.get_channel_details(top_channel_ids)
            
            # 채널 분석 결과 구성
            top_channels = []
            for channel_id in top_channel_ids:
                channel_info = channel_videos[channel_id]
                details = channel_details.get(channel_id, {})
                
                # 채널 성장률 추정
                growth_rate = await self._estimate_channel_growth(channel_id)
                
                # 콘텐츠 전략 분석
                content_strategy = self._analyze_content_strategy(channel_info['videos'])
                
                top_channels.append({
                    'channel_id': channel_id,
                    'channel_title': channel_info['channel_title'],
                    'subscriber_count': details.get('subscriber_count', 0),
                    'total_views': details.get('view_count', 0),
                    'video_count': details.get('video_count', 0),
                    'growth_rate': growth_rate,
                    'content_strategy': content_strategy,
                    'avg_views_per_video': details.get('view_count', 0) / max(1, details.get('video_count', 1)),
                    'relevant_videos': len(channel_info['videos'])
                })
            
            # 구독자 수로 정렬
            top_channels.sort(key=lambda x: x['subscriber_count'], reverse=True)
            
            return top_channels
            
        except Exception as e:
            logger.error(f"상위 채널 분석 오류: {e}")
            return []
    
    async def _analyze_content_gaps(self, keyword: str, top_channels: List[Dict]) -> List[str]:
        """콘텐츠 갭 분석"""
        
        content_gaps = []
        
        try:
            # 현재 콘텐츠 유형 수집
            existing_content_types = set()
            
            for channel in top_channels:
                strategy = channel.get('content_strategy', {})
                existing_content_types.update(strategy.get('content_types', []))
            
            # 잠재적 콘텐츠 갭 식별
            potential_gaps = {
                '튜토리얼': ['기초', '심화', '전문가'],
                '리뷰': ['제품', '서비스', '비교'],
                '브이로그': ['일상', '여행', '루틴'],
                '챌린지': ['24시간', '30일', '100일'],
                'Q&A': ['시청자 질문', 'FAQ', '전문가 인터뷰'],
                '시리즈': ['에피소드', '시즌제', '연재물']
            }
            
            # 채워지지 않은 갭 찾기
            for content_type, variations in potential_gaps.items():
                if f"{keyword} {content_type}" not in existing_content_types:
                    for variation in variations:
                        gap = f"{keyword} {content_type} - {variation}"
                        if gap not in existing_content_types:
                            content_gaps.append(gap)
            
            # 시즌별/트렌드 갭
            current_month = datetime.now().month
            seasonal_gaps = self._get_seasonal_gaps(keyword, current_month)
            content_gaps.extend(seasonal_gaps)
            
            # 타겟 청중별 갭
            audience_gaps = [
                f"{keyword} 초보자 가이드",
                f"{keyword} 전문가 팁",
                f"{keyword} 어린이용",
                f"{keyword} 시니어 가이드"
            ]
            
            for gap in audience_gaps:
                if gap not in existing_content_types:
                    content_gaps.append(gap)
            
        except Exception as e:
            logger.error(f"콘텐츠 갭 분석 오류: {e}")
        
        return content_gaps[:20]  # 상위 20개 갭
    
    def _analyze_upload_patterns(self, top_channels: List[Dict]) -> Dict[str, Any]:
        """업로드 패턴 분석"""
        
        patterns = {
            'optimal_upload_times': {},
            'frequency_analysis': {},
            'consistency_scores': {}
        }
        
        try:
            # 채널별 업로드 패턴 분석
            upload_times = []
            upload_frequencies = []
            
            for channel in top_channels:
                # 업로드 시간 분석 (더미 데이터 - 실제로는 영상 메타데이터 필요)
                channel_patterns = {
                    'preferred_days': ['월', '수', '금'],  # 예시
                    'preferred_hours': [19, 20, 21],  # 저녁 시간대
                    'videos_per_week': 3
                }
                
                upload_times.extend(channel_patterns['preferred_hours'])
                upload_frequencies.append(channel_patterns['videos_per_week'])
            
            # 최적 업로드 시간 계산
            if upload_times:
                from collections import Counter
                time_counter = Counter(upload_times)
                patterns['optimal_upload_times'] = {
                    'most_common_hours': time_counter.most_common(3),
                    'recommendation': f"{time_counter.most_common(1)[0][0]}시"
                }
            
            # 업로드 빈도 분석
            if upload_frequencies:
                patterns['frequency_analysis'] = {
                    'average_per_week': np.mean(upload_frequencies),
                    'minimum_competitive': min(upload_frequencies),
                    'maximum_observed': max(upload_frequencies)
                }
            
        except Exception as e:
            logger.error(f"업로드 패턴 분석 오류: {e}")
        
        return patterns
    
    def _analyze_collaboration_opportunities(self, top_channels: List[Dict]) -> List[Dict[str, Any]]:
        """협업 기회 분석"""
        
        opportunities = []
        
        try:
            # 채널 규모별 분류
            mega_channels = [ch for ch in top_channels if ch['subscriber_count'] > 1000000]
            large_channels = [ch for ch in top_channels if 100000 <= ch['subscriber_count'] <= 1000000]
            medium_channels = [ch for ch in top_channels if 10000 <= ch['subscriber_count'] < 100000]
            
            # 협업 기회 평가
            for channel in medium_channels[:5]:  # 중간 규모 채널이 협업 가능성 높음
                opportunity = {
                    'channel_title': channel['channel_title'],
                    'subscriber_count': channel['subscriber_count'],
                    'collaboration_score': self._calculate_collab_score(channel),
                    'suggested_content': [
                        "콜라보 챌린지",
                        "크로스 리뷰",
                        "공동 프로젝트",
                        "게스트 출연"
                    ],
                    'mutual_benefit': "상호 청중 확대 및 콘텐츠 다양화"
                }
                opportunities.append(opportunity)
            
            # 점수 기준 정렬
            opportunities.sort(key=lambda x: x['collaboration_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"협업 기회 분석 오류: {e}")
        
        return opportunities
    
    def _analyze_competitive_landscape(self, top_channels: List[Dict]) -> Dict[str, Any]:
        """경쟁 환경 분석"""
        
        landscape = {
            'market_saturation': 'medium',
            'entry_difficulty': 'medium',
            'growth_potential': 'high',
            'key_success_factors': [],
            'market_leaders': [],
            'emerging_players': []
        }
        
        try:
            # 시장 포화도 계산
            total_subs = sum(ch['subscriber_count'] for ch in top_channels)
            avg_subs = total_subs / len(top_channels) if top_channels else 0
            
            if avg_subs > 500000:
                landscape['market_saturation'] = 'high'
                landscape['entry_difficulty'] = 'high'
            elif avg_subs < 50000:
                landscape['market_saturation'] = 'low'
                landscape['entry_difficulty'] = 'low'
            
            # 성장 잠재력 평가
            growth_rates = [ch.get('growth_rate', 0) for ch in top_channels]
            avg_growth = np.mean(growth_rates) if growth_rates else 0
            
            if avg_growth > 20:
                landscape['growth_potential'] = 'very_high'
            elif avg_growth < 5:
                landscape['growth_potential'] = 'low'
            
            # 핵심 성공 요인
            landscape['key_success_factors'] = [
                "일관된 업로드 스케줄",
                "고품질 썸네일과 제목",
                "시청자 참여 유도",
                "트렌드 빠른 대응",
                "차별화된 콘텐츠 스타일"
            ]
            
            # 시장 리더와 신흥 채널 분류
            landscape['market_leaders'] = [
                {
                    'channel': ch['channel_title'],
                    'subscribers': ch['subscriber_count'],
                    'dominance': f"{(ch['subscriber_count'] / total_subs * 100):.1f}%"
                }
                for ch in top_channels[:3]
            ]
            
            landscape['emerging_players'] = [
                {
                    'channel': ch['channel_title'],
                    'growth_rate': ch.get('growth_rate', 0),
                    'potential': 'high' if ch.get('growth_rate', 0) > 30 else 'medium'
                }
                for ch in top_channels if ch.get('growth_rate', 0) > 20
            ][:3]
            
        except Exception as e:
            logger.error(f"경쟁 환경 분석 오류: {e}")
        
        return landscape
    
    async def _estimate_channel_growth(self, channel_id: str) -> float:
        """채널 성장률 추정"""
        # 실제 구현에서는 시계열 데이터 필요
        # 여기서는 더미 값 반환
        import random
        return random.uniform(-10, 50)
    
    def _analyze_content_strategy(self, videos: List[Dict]) -> Dict[str, Any]:
        """콘텐츠 전략 분석"""
        
        strategy = {
            'content_types': [],
            'title_patterns': [],
            'upload_frequency': 'unknown'
        }
        
        try:
            # 제목 패턴 분석
            title_keywords = []
            for video in videos:
                title = video['title'].lower()
                
                # 콘텐츠 유형 식별
                if any(word in title for word in ['튜토리얼', '강좌', '배우기']):
                    strategy['content_types'].append('교육')
                elif any(word in title for word in ['리뷰', '후기', '평가']):
                    strategy['content_types'].append('리뷰')
                elif any(word in title for word in ['브이로그', 'vlog', '일상']):
                    strategy['content_types'].append('브이로그')
                
                # 자주 사용되는 단어 추출
                words = title.split()
                title_keywords.extend(words)
            
            # 중복 제거
            strategy['content_types'] = list(set(strategy['content_types']))
            
        except Exception as e:
            logger.error(f"콘텐츠 전략 분석 오류: {e}")
        
        return strategy
    
    def _get_seasonal_gaps(self, keyword: str, month: int) -> List[str]:
        """계절별 콘텐츠 갭"""
        
        seasonal_content = {
            'spring': [f"{keyword} 봄 특집", f"{keyword} 벚꽃", f"{keyword} 새학기"],
            'summer': [f"{keyword} 여름 특집", f"{keyword} 휴가", f"{keyword} 더위"],
            'fall': [f"{keyword} 가을 특집", f"{keyword} 단풍", f"{keyword} 독서"],
            'winter': [f"{keyword} 겨울 특집", f"{keyword} 크리스마스", f"{keyword} 연말"]
        }
        
        if month in [3, 4, 5]:
            return seasonal_content['spring']
        elif month in [6, 7, 8]:
            return seasonal_content['summer']
        elif month in [9, 10, 11]:
            return seasonal_content['fall']
        else:
            return seasonal_content['winter']
    
    def _calculate_collab_score(self, channel: Dict) -> float:
        """협업 가능성 점수 계산"""
        
        score = 50.0
        
        # 구독자 수 (중간 규모가 높은 점수)
        subs = channel['subscriber_count']
        if 50000 <= subs <= 500000:
            score += 20
        elif 10000 <= subs < 50000:
            score += 15
        
        # 성장률
        growth = channel.get('growth_rate', 0)
        if growth > 30:
            score += 20
        elif growth > 10:
            score += 10
        
        # 콘텐츠 다양성
        content_types = channel.get('content_strategy', {}).get('content_types', [])
        if len(content_types) >= 3:
            score += 10
        
        return min(100, score)
    
    def _generate_competition_summary(self, 
                                    top_channels: List[Dict],
                                    content_gaps: List[str],
                                    landscape: Dict[str, Any]) -> Dict[str, str]:
        """경쟁 분석 요약 생성"""
        
        # 채널 평균 구독자
        avg_subs = np.mean([ch['subscriber_count'] for ch in top_channels]) if top_channels else 0
        
        summary = {
            'market_overview': f"시장 포화도: {landscape['market_saturation']}, "
                              f"평균 구독자: {avg_subs:,.0f}명",
            'entry_strategy': self._recommend_entry_strategy(landscape['market_saturation']),
            'content_opportunities': f"발견된 콘텐츠 갭: {len(content_gaps)}개",
            'top_gap': content_gaps[0] if content_gaps else "추가 분석 필요",
            'collaboration_potential': "중간" if len(top_channels) > 5 else "높음"
        }
        
        return summary
    
    def _recommend_entry_strategy(self, market_saturation: str) -> str:
        """시장 진입 전략 추천"""
        
        strategies = {
            'low': "블루오션 기회! 빠른 콘텐츠 제작으로 선점 효과 노리세요.",
            'medium': "차별화 전략 필요. 니치 타겟팅과 고품질 콘텐츠로 승부하세요.",
            'high': "포화 시장. 혁신적 포맷이나 콜라보레이션 전략을 고려하세요.",
            'unknown': "추가 시장 분석이 필요합니다."
        }
        
        return strategies.get(market_saturation, strategies['unknown'])
