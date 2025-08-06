# core/trend_analyzer.py 수정

import logging
from typing import Dict, List, Optional, Tuple, Callable
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
        
    async def analyze_keywords(self, keywords: List[str], category: Optional[str] = None, 
                              progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        여러 키워드를 배치로 분석
        
        Args:
            keywords: 분석할 키워드 리스트
            category: 카테고리
            progress_callback: 진행 상황 콜백 함수
            
        Returns:
            트렌드 분석 결과 리스트
        """
        results = []
        total = len(keywords)
        completed = 0
        
        # 배치 크기 설정 (Google Trends API 제한 고려)
        batch_size = 5
        
        for i in range(0, total, batch_size):
            batch = keywords[i:i+batch_size]
            
            try:
                # 배치 분석
                batch_data = self.trends_service.get_interest_over_time(batch)
                
                if batch_data is not None:
                    # 각 키워드별로 결과 처리
                    for keyword in batch:
                        if keyword in batch_data.columns:
                            keyword_data = batch_data[keyword]
                            
                            # 트렌드 방향 계산
                            trend_direction = self._calculate_trend_direction(keyword_data)
                            
                            # 평균 관심도
                            avg_interest = float(keyword_data.mean())
                            
                            results.append({
                                'keyword': keyword,
                                'trend_direction': trend_direction,
                                'average_interest': avg_interest,
                                'max_interest': float(keyword_data.max()),
                                'min_interest': float(keyword_data.min()),
                                'is_real_data': True,
                                'data_points': len(keyword_data)
                            })
                        else:
                            # 데이터가 없는 경우
                            results.append({
                                'keyword': keyword,
                                'trend_direction': 'unknown',
                                'average_interest': 0,
                                'max_interest': 0,
                                'min_interest': 0,
                                'is_real_data': False,
                                'data_points': 0
                            })
                else:
                    # 배치 전체 실패시 기본값
                    for keyword in batch:
                        results.append({
                            'keyword': keyword,
                            'trend_direction': 'unknown',
                            'average_interest': 0,
                            'max_interest': 0,
                            'min_interest': 0,
                            'is_real_data': False,
                            'data_points': 0
                        })
                        
            except Exception as e:
                logger.error(f"배치 분석 실패: {e}")
                # 실패한 배치의 키워드들에 대해 기본값 설정
                for keyword in batch:
                    results.append({
                        'keyword': keyword,
                        'trend_direction': 'unknown',
                        'average_interest': 0,
                        'max_interest': 0,
                        'min_interest': 0,
                        'is_real_data': False,
                        'data_points': 0
                    })
            
            # 진행 상황 업데이트
            completed += len(batch)
            if progress_callback:
                await progress_callback(completed, total)
            
            # API 제한 대응을 위한 대기
            if i + batch_size < total:
                await asyncio.sleep(2)  # 2초 대기
        
        return results
        
    def filter_keywords_first_pass(self, keywords: List, trend_results: List[Dict], 
                                  target_count: int = 60) -> List[Dict]:
        """
        1차 키워드 필터링 - 트렌드 데이터 기반
        
        Args:
            keywords: 확장된 키워드 리스트 (KeywordResult 객체들)
            trend_results: 트렌드 분석 결과
            target_count: 목표 키워드 수
            
        Returns:
            필터링된 키워드 리스트
        """
        # 트렌드 결과를 딕셔너리로 변환
        trend_dict = {result['keyword']: result for result in trend_results}
        
        # 키워드와 트렌드 데이터 결합
        keyword_data = []
        for kw in keywords:
            keyword_str = kw.keyword if hasattr(kw, 'keyword') else str(kw)
            trend_info = trend_dict.get(keyword_str, {})
            
            keyword_data.append({
                'keyword': keyword_str,
                'relevance': getattr(kw, 'relevance', 0.5),
                'trend_direction': trend_info.get('trend_direction', 'unknown'),
                'average_interest': trend_info.get('average_interest', 0),
                'is_real_data': trend_info.get('is_real_data', False)
            })
        
        # 점수 계산 및 정렬
        for data in keyword_data:
            score = 0
            
            # 관련성 점수
            score += data['relevance'] * 30
            
            # 트렌드 점수
            if data['trend_direction'] == 'rising':
                score += 20
            elif data['trend_direction'] == 'stable':
                score += 10
            
            # 평균 관심도 점수
            score += min(data['average_interest'] / 2, 30)
            
            # 실제 데이터 보너스
            if data['is_real_data']:
                score += 10
                
            data['score'] = score
        
        # 점수로 정렬
        sorted_keywords = sorted(keyword_data, key=lambda x: x['score'], reverse=True)
        
        return sorted_keywords[:target_count]
        
    def filter_keywords_second_pass(self, keywords: List[Dict], youtube_data: List[Dict], 
                                   competitor_data: Dict, target_count: int = 40) -> List[Dict]:
        """
        2차 키워드 필터링 - YouTube 데이터 기반
        
        Args:
            keywords: 1차 필터링된 키워드
            youtube_data: YouTube API 데이터
            competitor_data: 경쟁자 분석 데이터
            target_count: 목표 키워드 수
            
        Returns:
            최종 필터링된 키워드 리스트
        """
        # YouTube 데이터로 키워드 보강
        youtube_dict = {item['keyword']: item for item in youtube_data}
        
        # 기회 점수 계산
        for kw in keywords:
            keyword = kw['keyword'] if isinstance(kw, dict) else kw
            
            # YouTube 데이터 반영
            yt_data = youtube_dict.get(keyword, {})
            competition = yt_data.get('competition_level', 'medium')
            avg_views = yt_data.get('average_views', 0)
            
            # 경쟁자 데이터 반영
            comp_data = competitor_data.get(keyword, {})
            
            # 기회 점수 계산 (0-100)
            opportunity_score = 50.0
            
            # 경쟁도 반영
            if competition == 'low':
                opportunity_score += 20
            elif competition == 'high':
                opportunity_score -= 20
                
            # 평균 조회수 반영
            if avg_views > 100000:
                opportunity_score += 10
            elif avg_views < 10000:
                opportunity_score -= 10
                
            # 트렌드 반영
            if isinstance(kw, dict) and kw.get('trend_direction') == 'rising':
                opportunity_score += 15
            elif isinstance(kw, dict) and kw.get('trend_direction') == 'falling':
                opportunity_score -= 15
                
            # 점수 범위 제한
            opportunity_score = max(0, min(100, opportunity_score))
            
            # 결과 저장
            if isinstance(kw, dict):
                kw['opportunity_score'] = opportunity_score
                kw['competition_level'] = competition
                kw['average_views'] = avg_views
            else:
                # 단순 문자열인 경우 딕셔너리로 변환
                keywords[keywords.index(kw)] = {
                    'keyword': keyword,
                    'opportunity_score': opportunity_score,
                    'competition_level': competition,
                    'average_views': avg_views,
                    'trend_direction': 'unknown'
                }
        
        # 기회 점수로 정렬
        sorted_keywords = sorted(keywords, 
                               key=lambda x: x.get('opportunity_score', 0) if isinstance(x, dict) else 0, 
                               reverse=True)
        
        return sorted_keywords[:target_count]
        
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
            filtered_keywords = self.filter_keywords_basic(expanded_keywords)
            
            # 2차 필터링 (관련성)
            final_keywords = self.filter_keywords_by_relevance(filtered_keywords, keyword)
            
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
                logger.error(f"❌ 트렌드 데이터 획득 실패: {keyword}")
                return None  # 실패시 None 반환
                
        except Exception as e:
            logger.error(f"❌ 트렌드 분석 실패: {e}")
            return None  # 실패시 None 반환
            
    def filter_keywords_basic(self, keywords: List[str], max_keywords: int = 30) -> List[str]:
        """
        기본 키워드 필터링 - 중복 제거, 길이 제한 등
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
                
        logger.info(f"기본 필터링: {len(keywords)} → {len(filtered)} 키워드")
        return filtered
        
    def filter_keywords_by_relevance(self, keywords: List[str], base_keyword: str) -> List[str]:
        """
        관련성 기반 키워드 필터링
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
                
        logger.info(f"관련성 필터링: {len(keywords)} → {len(filtered)} 키워드")
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