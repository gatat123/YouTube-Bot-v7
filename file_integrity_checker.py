"""
YouTube Bot v7 파일 무결성 검사기
모든 Python 파일의 손상 여부를 체계적으로 검사합니다.
"""

import os
import sys
import ast
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import re

# Windows 환경에서의 인코딩 문제 해결
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

class FileIntegrityChecker:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.checked_files = []
        
    def check_all_files(self) -> Dict:
        """프로젝트의 모든 Python 파일을 검사합니다."""
        print("🔍 YouTube Bot v7 파일 무결성 검사 시작...")
        print(f"프로젝트 경로: {self.project_root}")
        print("=" * 70)
        
        # Python 파일 수집
        python_files = self._collect_python_files()
        print(f"\n📂 발견된 Python 파일: {len(python_files)}개")
        
        # 각 파일 검사
        for file_path in python_files:
            self._check_file(file_path)
            
        # 결과 요약
        return self._generate_report()
    
    def _collect_python_files(self) -> List[Path]:
        """프로젝트 내 모든 Python 파일을 수집합니다."""
        python_files = []
        # 제외할 디렉토리 확장 - 백업, 임시, 캐시 폴더 등
        exclude_dirs = {
            '.git', '__pycache__', 'venv', 'env', '.env', 'logs',
            'backup', 'backup_old_files', 'backups', 'old', 'archive',
            'temp', 'tmp', 'temporary', 'test_temp', 'cache',
            '.pytest_cache', '.coverage', 'htmlcov', 'build', 'dist',
            'node_modules', '.vscode', '.idea'
        }
        
        for root, dirs, files in os.walk(self.project_root):
            # 제외할 디렉토리 건너뛰기 (대소문자 무시)
            dirs[:] = [d for d in dirs if d.lower() not in {ex.lower() for ex in exclude_dirs}]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
                    
        return sorted(python_files)
    
    def _check_file(self, file_path: Path) -> None:
        """개별 파일을 검사합니다."""
        relative_path = file_path.relative_to(self.project_root)
        print(f"\n📄 검사 중: {relative_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_info = {
                'path': str(relative_path),
                'size': len(content),
                'lines': len(content.splitlines()),
                'issues': []
            }
            
            # 1. 빈 파일 검사
            if not content.strip():
                file_info['issues'].append({
                    'type': 'EMPTY_FILE',
                    'severity': 'HIGH',
                    'message': '파일이 비어있습니다'
                })
                
            # 2. 구문 검사 (AST 파싱)
            if content.strip():
                syntax_issues = self._check_syntax(content, relative_path)
                file_info['issues'].extend(syntax_issues)
                
            # 3. 구조 검사
            structure_issues = self._check_structure(content, relative_path)
            file_info['issues'].extend(structure_issues)
            
            # 4. 특정 패턴 검사
            pattern_issues = self._check_patterns(content, relative_path)
            file_info['issues'].extend(pattern_issues)
            
            # 결과 저장
            self.checked_files.append(file_info)
            
            if file_info['issues']:
                self.issues.append(file_info)
                print(f"   ⚠️  발견된 문제: {len(file_info['issues'])}개")
                for issue in file_info['issues']:
                    print(f"      - [{issue['severity']}] {issue['message']}")
            else:
                print("   ✅ 정상")
                
        except Exception as e:
            error_info = {
                'path': str(relative_path),
                'issues': [{
                    'type': 'READ_ERROR',
                    'severity': 'CRITICAL',
                    'message': f'파일 읽기 오류: {str(e)}'
                }]
            }
            self.issues.append(error_info)
            print(f"   ❌ 파일 읽기 실패: {e}")
    
    def _check_syntax(self, content: str, file_path: Path) -> List[Dict]:
        """Python 구문 검사를 수행합니다."""
        issues = []
        
        try:
            # AST 파싱 시도
            ast.parse(content)
        except SyntaxError as e:
            issues.append({
                'type': 'SYNTAX_ERROR',
                'severity': 'CRITICAL',
                'message': f'구문 오류 (줄 {e.lineno}): {e.msg}',
                'line': e.lineno
            })
        except Exception as e:
            issues.append({
                'type': 'PARSE_ERROR',
                'severity': 'HIGH',
                'message': f'파싱 오류: {str(e)}'
            })
            
        return issues
    
    def _check_structure(self, content: str, file_path: Path) -> List[Dict]:
        """파일 구조를 검사합니다."""
        issues = []
        lines = content.splitlines()
        
        # 1. 파일이 중간부터 시작하는지 검사
        if lines and len(lines) > 0:
            first_line = lines[0].strip()
            # 일반적인 파일 시작 패턴
            normal_starts = [
                '"""', "'''", '#', 'import ', 'from ', 'class ', 'def ', '@'
            ]
            
            if first_line and not any(first_line.startswith(s) for s in normal_starts):
                # 메서드 중간부터 시작하는 것 같은 경우
                if re.match(r'^\s+', lines[0]) or first_line.startswith('self.'):
                    issues.append({
                        'type': 'TRUNCATED_START',
                        'severity': 'CRITICAL',
                        'message': '파일이 중간부터 시작하는 것으로 보입니다'
                    })
        
        # 2. 클래스/함수 정의 완결성 검사
        if content.strip():
            incomplete_blocks = self._check_incomplete_blocks(content)
            issues.extend(incomplete_blocks)
            
        # 3. import 구문 검사
        import_issues = self._check_imports(content, file_path)
        issues.extend(import_issues)
        
        return issues
    
    def _check_incomplete_blocks(self, content: str) -> List[Dict]:
        """불완전한 코드 블록을 검사합니다."""
        issues = []
        lines = content.splitlines()
        
        if not lines:
            return issues
            
        # AST 파싱이 성공했다면 구문적으로는 완전한 파일
        try:
            ast.parse(content)
            # 구문적으로 완전하다면 들여쓰기 종료는 스타일 문제로만 분류
            last_line = lines[-1] if lines else ""
            if last_line and last_line[0].isspace() and last_line.strip():
                # 단순한 들여쓰기 종료 - LOW 심각도
                issues.append({
                    'type': 'INDENTED_END',
                    'severity': 'LOW',
                    'message': '파일이 들여쓰기된 라인으로 끝납니다 (스타일 문제)'
                })
        except SyntaxError:
            # 구문 오류가 있으면서 들여쓰기로 끝나는 경우 - 실제 문제
            last_line = lines[-1] if lines else ""
            if last_line and last_line[0].isspace() and last_line.strip():
                issues.append({
                    'type': 'INCOMPLETE_BLOCK',
                    'severity': 'HIGH',
                    'message': '파일이 불완전한 블록 중간에서 끝납니다'
                })
                
        # 명백히 중간에서 끊어진 케이스 확인
        if lines:
            last_line = lines[-1].strip()
            # 콜론으로 끝나면서 다음 블록이 없는 경우
            if last_line.endswith(':') and len([l for l in lines if l.strip()]) > 0:
                # 마지막 비어있지 않은 라인이 콜론으로 끝나는지 확인
                non_empty_lines = [l for l in lines if l.strip()]
                if non_empty_lines and non_empty_lines[-1].strip().endswith(':'):
                    issues.append({
                        'type': 'INCOMPLETE_BLOCK',
                        'severity': 'MEDIUM',
                        'message': '블록 정의 후 내용이 없습니다'
                    })
                
        return issues
    
    def _check_imports(self, content: str, file_path: Path) -> List[Dict]:
        """import 구문을 검사합니다."""
        issues = []
        
        # __init__.py 파일의 경우 특별 처리
        if file_path.name == '__init__.py':
            # 모듈 import 검사
            if 'core' in str(file_path):
                expected_imports = ['KeywordExpander', 'TrendAnalyzer', 
                                  'CompetitorAnalyzer', 'PredictionEngine']
            elif 'services' in str(file_path):
                expected_imports = ['YouTubeService', 'TrendsService', 
                                  'generate_titles_with_gemini']
            elif 'utils' in str(file_path):
                expected_imports = ['CacheManager', 'ProgressTracker', 
                                  'APIManager']
            else:
                expected_imports = []
                
            for expected in expected_imports:
                if expected not in content:
                    issues.append({
                        'type': 'MISSING_IMPORT',
                        'severity': 'MEDIUM',
                        'message': f'예상되는 import 누락: {expected}'
                    })
                    
        return issues
    
    def _check_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """특정 패턴과 이상 징후를 검사합니다."""
        issues = []
        
        # 1. 파일 종료 패턴 검사 (완화된 기준)
        if content.strip():
            last_line = content.splitlines()[-1] if content.splitlines() else ""
            # 더 관대한 파일 끝 검사 - 개행문자 누락은 스타일 문제로 분류
            if last_line.strip() and not content.endswith('\n'):
                # 단순 개행문자 누락은 LOW 심각도
                issues.append({
                    'type': 'MISSING_NEWLINE',
                    'severity': 'LOW',
                    'message': '파일 끝에 개행문자가 없습니다 (스타일 문제)'
                })
            elif last_line.strip() and last_line.strip().endswith('\\'):
                # 백슬래시로 끝나는 경우는 실제 문제일 가능성
                issues.append({
                    'type': 'ABRUPT_END',
                    'severity': 'MEDIUM',
                    'message': '파일이 비정상적으로 끝나는 것으로 보입니다 (백슬래시 종료)'
                })
        
        # 2. 특정 파일별 검사
        if 'keyword_expander' in str(file_path):
            # 90개 키워드 확장 메서드 확인
            required_methods = [
                '_expand_core_keywords',
                '_expand_search_intent_keywords',
                '_expand_target_audience_keywords',
                '_expand_temporal_keywords',
                '_expand_long_tail_keywords'
            ]
            
            for method in required_methods:
                if method not in content:
                    issues.append({
                        'type': 'MISSING_METHOD',
                        'severity': 'HIGH',
                        'message': f'필수 메서드 누락: {method}'
                    })
                    
        return issues
    
    def _generate_report(self) -> Dict:
        """검사 결과 보고서를 생성합니다."""
        total_files = len(self.checked_files)
        
        # 심각도별 이슈 집계 및 분류
        severity_count = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        issue_types = {}
        
        # 실제 문제와 스타일 문제 분리
        critical_files = []  # CRITICAL, HIGH 문제가 있는 파일
        functional_files = []  # MEDIUM 문제가 있는 파일  
        style_only_files = []  # LOW 문제만 있는 파일
        
        for file_info in self.issues:
            has_critical = False
            has_functional = False
            has_style = False
            
            for issue in file_info['issues']:
                severity = issue.get('severity', 'MEDIUM')
                severity_count[severity] += 1
                
                issue_type = issue.get('type', 'UNKNOWN')
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
                
                if severity in ['CRITICAL', 'HIGH']:
                    has_critical = True
                elif severity == 'MEDIUM':
                    has_functional = True
                elif severity == 'LOW':
                    has_style = True
            
            # 파일 분류 (우선순위: CRITICAL > FUNCTIONAL > STYLE)
            if has_critical:
                critical_files.append(file_info)
            elif has_functional:
                functional_files.append(file_info)
            elif has_style:
                style_only_files.append(file_info)
        
        # 개선된 건강도 계산 (스타일 문제는 가중치 50% 적용)
        style_files_weight = len(style_only_files) * 0.5
        problematic_files = len(critical_files) + len(functional_files) + style_files_weight
        functional_health = round((total_files - problematic_files) / total_files * 100, 2) if total_files > 0 else 0
        
        # 기존 건강도 (하위 호환성)
        files_with_issues = len(self.issues)
        basic_health = round((total_files - files_with_issues) / total_files * 100, 2) if total_files > 0 else 0
        
        report = {
            'scan_date': datetime.now().isoformat(),
            'project_root': str(self.project_root),
            'summary': {
                'total_files_scanned': total_files,
                'files_with_issues': files_with_issues,
                'critical_files': len(critical_files),
                'functional_files': len(functional_files), 
                'style_only_files': len(style_only_files),
                'healthy_files': total_files - files_with_issues,
                'health_percentage': basic_health,  # 기존 방식
                'functional_health_percentage': functional_health  # 개선된 방식
            },
            'severity_breakdown': severity_count,
            'issue_types': issue_types,
            'detailed_issues': self.issues,
            'categorized_issues': {
                'critical_files': critical_files,
                'functional_files': functional_files,
                'style_only_files': style_only_files
            }
        }
        
        # 개선된 보고서 출력
        print("\n" + "=" * 70)
        print("📊 검사 결과 요약")
        print("=" * 70)
        print(f"총 검사 파일: {total_files}개")
        print(f"정상 파일: {total_files - files_with_issues}개")
        print(f"전체 건강도: {report['summary']['health_percentage']}%")
        print(f"기능적 건강도: {report['summary']['functional_health_percentage']}%")
        
        # 파일 분류별 결과
        print(f"\n📋 파일 분류:")
        print(f"  🚨 긴급 수정 필요 (Critical/High): {len(critical_files)}개")
        print(f"  ⚠️  검토 권장 (Medium): {len(functional_files)}개") 
        print(f"  📝 스타일 개선 (Low): {len(style_only_files)}개")
        print(f"  ✅ 정상 파일: {total_files - files_with_issues}개")
        
        print(f"\n🔍 심각도별 이슈:")
        severity_icons = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🔵'}
        for severity, count in severity_count.items():
            if count > 0:
                icon = severity_icons.get(severity, '⚪')
                print(f"  {icon} {severity}: {count}개")
        
        # 긴급 수정이 필요한 파일들만 출력
        if critical_files:
            print(f"\n🚨 즉시 수정 필요한 파일들:")
            for file_info in critical_files:
                print(f"  📁 {file_info['path']}")
                critical_issues = [i for i in file_info['issues'] 
                                 if i['severity'] in ['CRITICAL', 'HIGH']]
                for issue in critical_issues:
                    severity_color = '🔴' if issue['severity'] == 'CRITICAL' else '🟠'
                    print(f"     {severity_color} {issue['message']}")
        
        if functional_files:
            print(f"\n⚠️  검토 권장 파일들:")
            for file_info in functional_files:
                print(f"  📁 {file_info['path']}")
                medium_issues = [i for i in file_info['issues'] if i['severity'] == 'MEDIUM']
                for issue in medium_issues:
                    print(f"     🟡 {issue['message']}")
        
        if style_only_files:
            print(f"\n📝 스타일 개선 권장 파일들 ({len(style_only_files)}개):")
            print(f"   (Python 실행에는 영향 없는 스타일 문제들)")
            if len(style_only_files) <= 5:  # 5개 이하면 모두 표시
                for file_info in style_only_files:
                    print(f"  📄 {file_info['path']}")
            else:  # 너무 많으면 일부만 표시
                for file_info in style_only_files[:3]:
                    print(f"  📄 {file_info['path']}")
                print(f"  ... 및 {len(style_only_files)-3}개 추가 파일")
                
        print(f"\n📈 이슈 유형별 분포:")
        for issue_type, count in issue_types.items():
            print(f"  - {issue_type}: {count}개")
            
        # JSON 파일로 저장
        report_path = self.project_root / 'file_integrity_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"\n📋 상세 보고서 저장됨: {report_path}")
        
        return report


def main():
    """메인 실행 함수"""
    try:
        # 현재 스크립트가 있는 디렉토리를 기본 프로젝트 루트로 설정
        script_dir = Path(__file__).parent.resolve()
        project_root = str(script_dir)
        
        print(f"📁 프로젝트 루트: {project_root}")
        
        checker = FileIntegrityChecker(project_root)
        report = checker.check_all_files()
        
        # 심각한 문제가 있는 파일 목록 출력
        if report['detailed_issues']:
            print("\n⚠️  주의가 필요한 파일:")
            for file_info in report['detailed_issues']:
                critical_issues = [i for i in file_info['issues'] 
                                 if i['severity'] in ['CRITICAL', 'HIGH']]
                if critical_issues:
                    print(f"\n  📌 {file_info['path']}:")
                    for issue in critical_issues:
                        print(f"     - [{issue['severity']}] {issue['message']}")
        else:
            print("\n🎉 모든 파일이 정상 상태입니다!")
        
        # 실행 완료 메시지
        print("\n" + "="*70)
        print("✅ 파일 무결성 검사가 성공적으로 완료되었습니다.")
        return report
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 검사를 중단했습니다.")
        return None
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
        print("   스크립트 실행을 다시 시도해보세요.")
        return None


if __name__ == "__main__":
    main()
