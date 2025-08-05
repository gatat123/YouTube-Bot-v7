"""
Gemini API 서비스 - 제목 생성
"""

import google.generativeai as genai
import re
import json
import logging
from typing import List, Dict, Any, Optional
import asyncio

from config import config

logger = logging.getLogger(__name__)


async def generate_titles_with_gemini(keywords: List[str], 
                                    category: Optional[str] = None) -> List[str]:
    """Gemini를 사용한 제목 생성"""
    
    if not config.api.gemini_key:
        return []
    
    try:
        genai.configure(api_key=config.api.gemini_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # 프롬프트 생성
        prompt = f"""YouTube 제목 최적화 전문가로서 작업해주세요.

주요 키워드: {', '.join(keywords[:5])}
카테고리: {category or '일반'}

다음 후킹 패턴을 활용하여 5개의 제목을 생성하세요:
1. 손해 회피: "모르면 손해" 심리
2. 호기심 자극: 궁금증 유발
3. 숫자 활용: 명확한 구조
4. Before/After: 변화 강조
5. 권위 도전: 상식 뒤집기

요구사항:
- 60자 이내
- 자연스러운 한국어
- 과도한 클릭베이트 지양
- 키워드 자연스럽게 포함

JSON 형식으로 응답:
{
  "titles": [
    {"title": "제목1", "hook_type": "손해 회피"},
    {"title": "제목2", "hook_type": "호기심 자극"},
    {"title": "제목3", "hook_type": "숫자 활용"},
    {"title": "제목4", "hook_type": "Before/After"},
    {"title": "제목5", "hook_type": "권위 도전"}
  ]
}"""

        # 비동기 실행
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            model.generate_content,
            prompt
        )
        
        # 응답 파싱
        response_text = response.text
        
        # JSON 추출
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            titles = [item['title'] for item in data.get('titles', [])]
            return titles[:5]
        else:
            # JSON이 아닌 경우 라인별 파싱
            lines = response_text.strip().split('\n')
            titles = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('{') and len(line) < 100:
                    # 번호나 특수문자 제거
                    clean_title = re.sub(r'^\d+\.\s*', '', line)
                    clean_title = re.sub(r'^[-•*]\s*', '', clean_title)
                    if clean_title:
                        titles.append(clean_title)
            
            return titles[:5]
            
    except Exception as e:
        logger.error(f"Gemini 제목 생성 오류: {e}")
        return []
