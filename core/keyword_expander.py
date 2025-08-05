"""
키워드 확장 모듈 - Gemini AI를 활용한 90개 키워드 확장

=====================================
[변경 이력]
- 2025-01-31: Claude AI → Gemini 2.5 Pro 변경
- 2025-01-31: 핵심 키워드 30개 → 40개 확장
- 2025-01-31: 파일 복구 (구문 오류 해결)
=====================================
"""

import asyncio
import json
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import aiohttp
import logging

from config import config

logger = logging.getLogger(__name__)


@dataclass
class ExpandedKeyword:
    """확장된 키워드 정보"""
    keyword: str
    category: str  # core, search_intent, target, temporal, long_tail
    relevance_score: float = 1.0
    metadata: Dict = field(default_factory=dict)


class KeywordExpander:
    """
    Gemini AI 기반 키워드 확장기 (20개 → 90개)
    
    =====================================
    [변경] Claude AI → Gemini AI 변경 (2025-01-31)
    이유: Gemini 2.5 Pro 모델 적용을 위한 API 변경
    기존: Claude API (Anthropic)
    변경: Gemini API (Google)
    =====================================
    """
    
    def __init__(self):
        # =====================================
        # [변경] API 설정 변경 (2025-01-31)
        # 이유: Claude API → Gemini API 변경
        # 기존: anthropic_key, Claude API URL
        # 변경: gemini_key, Gemini API URL
        # =====================================
        self.api_key = config.api.gemini_key  # [변경] anthropic_key → gemini_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"  # [변경] Claude API URL → Gemini API URL (Gemini 2.5 Pro)
        self.headers = {
            "Content-Type": "application/json"  # [변경] Gemini API 헤더 형식으로 변경
        }
        self.expansion_config = config.analysis.keyword_expansion
    
    async def expand_keywords(self, 
                            base_text: str, 
                            category: Optional[str] = None,
                            user_keywords: Optional[List[str]] = None) -> List[ExpandedKeyword]:
        """
        키워드를 90개로 확장
        
        =====================================
        [변경] 핵심 키워드 확장량 증가 (2025-01-31)
        이유: 2단계 필터링 강화를 위한 핵심 키워드 증량
        기존: 30+20+15+10+15 = 90개
        변경: 40+20+15+10+15 = 100개 → 상위 90개 선택
        =====================================
        
        Args:
            base_text: 기본 텍스트/주제
            category: 콘텐츠 카테고리
            user_keywords: 사용자 제공 키워드
            
        Returns:
            확장된 키워드 리스트 (90개)
        """
        # 병렬로 여러 확장 작업 실행
        tasks = [
            self._expand_core_keywords(base_text, category, user_keywords),  # [변경] 30개 → 40개
            self._expand_search_intent_keywords(base_text, category),
            self._expand_target_audience_keywords(base_text, category),
            self._expand_temporal_keywords(base_text, category),
            self._expand_long_tail_keywords(base_text, category, user_keywords)
        ]
        
        # 모든 확장 작업 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 통합
        all_keywords = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"키워드 확장 오류 (작업 {i}): {result}")
                continue
            all_keywords.extend(result)
        
        # 중복 제거 및 정렬
        unique_keywords = self._deduplicate_keywords(all_keywords)
        
        # 상위 90개 선택
        return unique_keywords[:90]
    
    async def _expand_core_keywords(self, 
                                  text: str, 
                                  category: Optional[str],
                                  user_keywords: Optional[List[str]]) -> List[ExpandedKeyword]:
        """
        핵심 키워드 확장 (40개)
        
        =====================================
        [변경] 핵심 키워드 확장 30개 → 40개 (2025-01-31)
        이유: 2단계 필터링 강화를 위한 핵심 키워드 증량
        기존: 30개 (동의어 10개, 축약어 5개, 하위주제 5개)
        변경: 40개 (동의어 20개, 축약어 10개, 하위주제 10개)
        =====================================
        """
        
        category_context = ""
        if category:
            cat_config = config.categories.categories.get(category, {})
            category_context = f"""
카테고리: {category}
카테고리 키워드: {', '.join(cat_config.get('keywords', []))}
부스트 단어: {', '.join(cat_config.get('boost_words', []))}
"""
        
        user_context = ""
        if user_keywords:
            user_context = f"\n사용자 제공 키워드: {', '.join(user_keywords[:5])}"
        
        prompt = f"""YouTube 키워드 전문가로서 핵심 키워드를 확장해주세요.

주제: {text}
{category_context}
{user_context}

다음 형식으로 40개의 핵심 키워드를 생성하세요:
1. 직접 동의어 및 유사어 (20개)
2. 축약어 및 별칭 (10개)
3. 영어/한국어 변형 (5개)
4. 관련 브랜드/제품명 (5개)
5. 구체적 하위 주제 (10개)

요구사항:
- 실제 YouTube에서 많이 검색되는 형태
- 자연스러운 검색어 형태
- 중복 없이 다양하게

JSON 배열로만 응답: ["키워드1", "키워드2", ...]"""

        keywords = await self._call_gemini_api(prompt)  # [변경] _call_claude_api → _call_gemini_api
        
        return [
            ExpandedKeyword(
                keyword=kw,
                category='core',
                relevance_score=1.0 - (i * 0.02),  # 순서대로 점수 감소
                metadata={'type': 'core', 'rank': i+1}
            )
            for i, kw in enumerate(keywords[:40])  # [변경] 30개 → 40개
        ]
    
    async def _expand_search_intent_keywords(self, text: str, category: Optional[str]) -> List[ExpandedKeyword]:
        """검색 의도별 키워드 확장 (20개)"""
        
        prompt = f"""YouTube 검색 의도별 키워드를 생성하세요.

주제: {text}
카테고리: {category or '일반'}

검색 의도별로 각 5개씩:
1. 정보성 (How to, 방법, 뜻, 이란)
2. 학습형 (강의, 강좌, 배우기, 기초)
3. 비교형 (vs, 비교, 차이, 장단점)
4. 문제해결형 (해결, 오류, 안될때, 고치는법)

실제 사용자들이 검색하는 자연스러운 형태로 작성하세요.

JSON 배열로만 응답: ["키워드1", "키워드2", ...]"""

        keywords = await self._call_gemini_api(prompt)  # [변경] _call_claude_api → _call_gemini_api
        
        intent_types = ['informational', 'educational', 'comparative', 'troubleshooting']
        
        return [
            ExpandedKeyword(
                keyword=kw,
                category='search_intent',
                relevance_score=0.9 - (i * 0.02),
                metadata={
                    'intent_type': intent_types[i // 5] if i < 20 else 'general',
                    'rank': i+1
                }
            )
            for i, kw in enumerate(keywords[:20])
        ]
    
    async def _expand_target_audience_keywords(self, text: str, category: Optional[str]) -> List[ExpandedKeyword]:
        """타겟 대상별 키워드 확장 (15개)"""
        
        prompt = f"""타겟 시청자별 YouTube 키워드를 생성하세요.

주제: {text}
카테고리: {category or '일반'}

타겟별로 각 5개씩:
1. 초보자용 (입문, 기초, 쉽게, 처음)
2. 중급자용 (심화, 꿀팁, 노하우)
3. 전문가용 (고급, 프로, 전문가)

각 수준에 맞는 자연스러운 검색어로 작성하세요.

JSON 배열로만 응답: ["키워드1", "키워드2", ...]"""

        keywords = await self._call_gemini_api(prompt)  # [변경] _call_claude_api → _call_gemini_api
        
        audience_levels = ['beginner', 'intermediate', 'expert']
        
        return [
            ExpandedKeyword(
                keyword=kw,
                category='target',
                relevance_score=0.85 - (i * 0.02),
                metadata={
                    'audience_level': audience_levels[i // 5] if i < 15 else 'general',
                    'rank': i+1
                }
            )
            for i, kw in enumerate(keywords[:15])
        ]
    
    async def _expand_temporal_keywords(self, text: str, category: Optional[str]) -> List[ExpandedKeyword]:
        """시간/상황별 키워드 확장 (10개)"""
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        season = self._get_current_season(current_month)
        
        prompt = f"""시간/트렌드 관련 YouTube 키워드를 생성하세요.

주제: {text}
카테고리: {category or '일반'}
현재: {current_year}년 {current_month}월 ({season})

다음 형식으로 10개 생성:
1. 연도별 (2024, 2025, 최신)
2. 시즌별 ({season} 관련)
3. 트렌드 (신규, 업데이트, 핫한)
4. 이벤트 (관련 이벤트/기념일)

시의성 있는 자연스러운 검색어로 작성하세요.

JSON 배열로만 응답: ["키워드1", "키워드2", ...]"""

        keywords = await self._call_gemini_api(prompt)  # [변경] _call_claude_api → _call_gemini_api
        
        return [
            ExpandedKeyword(
                keyword=kw,
                category='temporal',
                relevance_score=0.8 - (i * 0.02),
                metadata={
                    'temporal_type': self._get_temporal_type(kw),
                    'season': season,
                    'rank': i+1
                }
            )
            for i, kw in enumerate(keywords[:10])
        ]
    
    async def _expand_long_tail_keywords(self, 
                                       text: str, 
                                       category: Optional[str],
                                       user_keywords: Optional[List[str]]) -> List[ExpandedKeyword]:
        """롱테일 키워드 조합 (15개)"""
        
        base_keywords = user_keywords[:3] if user_keywords else []
        
        prompt = f"""롱테일 YouTube 검색 키워드를 생성하세요.

주제: {text}
카테고리: {category or '일반'}
기본 키워드: {', '.join(base_keywords) if base_keywords else '없음'}

3-5단어로 구성된 자연스러운 롱테일 키워드 15개 생성:
- 구체적인 상황/문제 설명
- 자연스러운 한국어 구어체
- 실제 검색될 만한 형태

예시: "마인크래프트 초보자 집 짓기 쉽게"

JSON 배열로만 응답: ["키워드1", "키워드2", ...]"""

        keywords = await self._call_gemini_api(prompt)  # [변경] _call_claude_api → _call_gemini_api
        
        return [
            ExpandedKeyword(
                keyword=kw,
                category='long_tail',
                relevance_score=0.75 - (i * 0.02),
                metadata={
                    'word_count': len(kw.split()),
                    'rank': i+1
                }
            )
            for i, kw in enumerate(keywords[:15])
        ]
    
    async def _call_gemini_api(self, prompt: str) -> List[str]:
        """
        Gemini API 호출
        
        =====================================
        [변경] Claude API → Gemini API 호출 (2025-01-31)
        이유: Gemini 2.5 Pro 모델 적용
        기존: Claude API 호출 구조
        변경: Gemini API 호출 구조
        =====================================
        """
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1000,
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}?key={self.api_key}",  # [변경] Gemini API URL 형식
                    headers=self.headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['candidates'][0]['content']['parts'][0]['text']  # [변경] Gemini API 응답 구조
                        
                        # JSON 파싱
                        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
                        if json_match:
                            keywords = json.loads(json_match.group())
                            return [kw.strip() for kw in keywords if kw.strip()]
                    else:
                        logger.error(f"Gemini API 오류: {response.status}")  # [변경] 오류 메시지
                        
        except asyncio.TimeoutError:
            logger.error("Gemini API 타임아웃")  # [변경] 오류 메시지
        except Exception as e:
            logger.error(f"Gemini API 호출 오류: {e}")  # [변경] 오류 메시지
        
        return []
    
    def _deduplicate_keywords(self, keywords: List[ExpandedKeyword]) -> List[ExpandedKeyword]:
        """중복 키워드 제거 및 정렬"""
        seen = set()
        unique = []
        
        # 정규화 함수
        def normalize(keyword: str) -> str:
            return keyword.lower().replace(' ', '').replace('-', '')
        
        # 점수순으로 정렬
        sorted_keywords = sorted(keywords, key=lambda x: x.relevance_score, reverse=True)
        
        for kw in sorted_keywords:
            normalized = normalize(kw.keyword)
            if normalized not in seen:
                seen.add(normalized)
                unique.append(kw)
        
        return unique
    
    def _get_current_season(self, month: int) -> str:
        """현재 시즌 반환"""
        if month in [3, 4, 5]:
            return "봄"
        elif month in [6, 7, 8]:
            return "여름"
        elif month in [9, 10, 11]:
            return "가을"
        else:
            return "겨울"
    
    def _get_temporal_type(self, keyword: str) -> str:
        """시간 관련 키워드 타입 판별"""
        if any(year in keyword for year in ['2024', '2025', '최신']):
            return 'yearly'
        elif any(season in keyword for season in ['봄', '여름', '가을', '겨울']):
            return 'seasonal'
        elif any(trend in keyword for trend in ['신규', '업데이트', '핫한', '트렌드']):
            return 'trending'
        else:
            return 'event'