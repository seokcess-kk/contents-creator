"""키워드 노출 난이도 분석 도메인.

격리 도메인 (격리 등급 STAGE_ORDER=0). 다른 도메인을 직접 import 하지 않으며,
SERP fetch 는 application 레이어가 `domain.crawler.brightdata_client.BrightDataClient`
인스턴스를 의존성 주입한다 (ranking 도메인과 동일한 DI 패턴).

사용처:
- application/keyword_difficulty_orchestrator.analyze_keyword
- application/keyword_difficulty_orchestrator.batch_analyze_keywords
"""
