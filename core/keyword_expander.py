intent_keywords(self, 
                                           text: str, 
                                           category: Optional[str]) -> List[ExpandedKeyword]:
        """검색 의도별 키워드 확장 (20개)"""
        
        prompt = f"""YouTube 검색 의도별 키워드를 생성해주세요.

주제: {text}
카테고리: {category if category else "일반"}

다음 검색 의도별로 각 5개씩, 총 20개의 키워드를 생성해주세요:

1. 정보성 검색 (how, what, why 등): 5개
2. 학습/튜토리얼 검색 (tutorial, guide, learn): 5개
3. 비교/리뷰 검색 (vs, best, review): 5개
4. 문제해결 검색 (fix, solve, error): 5개

각 키워드는 한 줄에 하나씩, 실제 YouTube에서 검색될 만한 형태로 작성해주세요."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                safety_settings=self.safety_settings
            )
            
            keywords_text = response.text
            keywords = self._parse_keywords(keywords_text)[:20]
            
            return [
                ExpandedKeyword(
                    keyword=kw,
                    category="search_intent",
                    relevance_score=0.9,
                    metadata={"intent_type": self._determine_intent_type(kw)}
                )
                for kw in keywords
            ]
        except Exception as e:
            logger.error(f"검색 의도 키워드 확장 실패: {e}")
            return []
    
    async def _expand_target_audience_keywords(self, 
                                             text: str, 
                                             category: Optional[str]) -> List[ExpandedKeyword]:
        """타겟 대상별 키워드 확장 (15개)"""
        
        prompt = f"""YouTube 타겟 시청자별 키워드를 생성해주세요.

주제: {text}
카테고리: {category if category else "일반"}

다음 타겟 그룹별로 각 5개씩, 총 15개의 키워드를 생성해주세요:

1. 초보자/입문자용: 5개
2. 중급자/실무자용: 5개
3. 전문가/고급자용: 5개

각 키워드는 해당 수준의 시청자가 실제로 검색할 만한 형태로 작성해주세요."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                safety_settings=self.safety_settings
            )
            
            keywords_text = response.text
            keywords = self._parse_keywords(keywords_text)[:15]
            
            return [
                ExpandedKeyword(
                    keyword=kw,
                    category="target",
                    relevance_score=0.85,
                    metadata={"audience_level": self._determine_audience_level(kw)}
                )
                for kw in keywords
            ]
        except Exception as e:
            logger.error(f"타겟 대상 키워드 확장 실패: {e}")
            return []
    
    async def _expand_temporal_keywords(self, 
                                      text: str, 
                                      category: Optional[str]) -> List[ExpandedKeyword]:
        """시간/상황별 키워드 확장 (10개)"""
        
        current_year = datetime.now().year
        current_month = datetime.now().strftime("%B")
        
        prompt = f"""YouTube 시간/트렌드 관련 키워드를 생성해주세요.

주제: {text}
카테고리: {category if category else "일반"}
현재: {current_year}년 {current_month}

다음 시간/상황별로 총 10개의 키워드를 생성해주세요:

1. 최신/트렌드 키워드 ({current_year}, latest, new): 5개
2. 시즌/이벤트 키워드 (계절, 행사, 기념일): 3개
3. 버전/업데이트 키워드: 2개

각 키워드는 현재 시점에서 인기 있을 만한 형태로 작성해주세요."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                safety_settings=self.safety_settings
            )
            
            keywords_text = response.text
            keywords = self._parse_keywords(keywords_text)[:10]
            
            return [
                ExpandedKeyword(
                    keyword=kw,
                    category="temporal",
                    relevance_score=0.95,  # 시간성 키워드는 높은 점수
                    metadata={"temporal_type": "trending"}
                )
                for kw in keywords
            ]
        except Exception as e:
            logger.error(f"시간별 키워드 확장 실패: {e}")
            return []
    
    async def _expand_long_tail_keywords(self, 
                                       text: str, 
                                       category: Optional[str],
                                       user_keywords: Optional[List[str]]) -> List[ExpandedKeyword]:
        """롱테일 키워드 확장 (15개)"""
        
        user_context = ""
        if user_keywords:
            user_context = f"\n참고 키워드: {', '.join(user_keywords[:3])}"
        
        prompt = f"""YouTube 롱테일 키워드를 생성해주세요.

주제: {text}
카테고리: {category if category else "일반"}
{user_context}

3-5단어로 구성된 구체적이고 자연스러운 롱테일 키워드 15개를 생성해주세요.
이 키워드들은:
- 실제 사용자가 검색할 만한 자연스러운 문구
- 구체적인 상황이나 문제를 포함
- 경쟁이 낮지만 관련성이 높은 키워드

각 키워드는 한 줄에 하나씩 작성해주세요."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                safety_settings=self.safety_settings
            )
            
            keywords_text = response.text
            keywords = self._parse_keywords(keywords_text)[:15]
            
            return [
                ExpandedKeyword(
                    keyword=kw,
                    category="long_tail",
                    relevance_score=0.8,
                    metadata={"word_count": len(kw.split())}
                )
                for kw in keywords
            ]
        except Exception as e:
            logger.error(f"롱테일 키워드 확장 실패: {e}")
            return []
    
    def _parse_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 줄바꿈으로 분리
        lines = text.strip().split('\n')
        
        keywords = []
        for line in lines:
            # 번호, 대시, 불릿 제거
            cleaned = re.sub(r'^[\d\-\*\•\.]+\s*', '', line.strip())
            # 콜론 이후 텍스트만 추출 (카테고리 표시 제거)
            if ':' in cleaned:
                cleaned = cleaned.split(':', 1)[-1].strip()
            
            # 빈 문자열이 아니고 너무 길지 않은 경우만 추가
            if cleaned and len(cleaned) < 100:
                keywords.append(cleaned.lower())
        
        return keywords
    
    def _deduplicate_keywords(self, keywords: List[ExpandedKeyword]) -> List[ExpandedKeyword]:
        """중복 키워드 제거 및 정렬"""
        seen = set()
        unique = []
        
        # 점수 기준 정렬
        sorted_keywords = sorted(keywords, key=lambda x: x.relevance_score, reverse=True)
        
        for kw in sorted_keywords:
            normalized = kw.keyword.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(kw)
        
        return unique
    
    def _determine_intent_type(self, keyword: str) -> str:
        """검색 의도 유형 판단"""
        keyword_lower = keyword.lower()
        
        if any(word in keyword_lower for word in ['how', 'what', 'why', 'when', 'where']):
            return "informational"
        elif any(word in keyword_lower for word in ['tutorial', 'guide', 'learn', 'course']):
            return "educational"
        elif any(word in keyword_lower for word in ['vs', 'versus', 'best', 'review', 'compare']):
            return "comparison"
        elif any(word in keyword_lower for word in ['fix', 'solve', 'error', 'problem', 'issue']):
            return "problem_solving"
        else:
            return "general"
    
    def _determine_audience_level(self, keyword: str) -> str:
        """시청자 수준 판단"""
        keyword_lower = keyword.lower()
        
        if any(word in keyword_lower for word in ['beginner', 'basic', 'intro', 'start', 'easy']):
            return "beginner"
        elif any(word in keyword_lower for word in ['advanced', 'expert', 'pro', 'master']):
            return "expert"
        else:
            return "intermediate"