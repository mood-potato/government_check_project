# TODOS — 국회의원 모순 탐지기

Phase 2/3 아이디어 및 기술 부채. 현재 스코프 밖.

---

## Phase 2 (모순 탐지 API MVP 품질 검증 후)

- [ ] **NLI 파일럿**: `klue/roberta-base` 기반 자연어 추론 모델로 발언 쌍의 실제 모순 여부 분류. all-MiniLM-L6-v2의 cosine distance 한계를 보완. 파일럿 테스트로 정확도 비교 후 도입 결정.
- [ ] **알림 구독**: 특정 주제 또는 의원에 대한 새로운 모순 발언 발생 시 이메일/RSS 알림. 구독 DB 스키마 및 발송 파이프라인 필요.
- [ ] **한국어 전용 임베딩 모델 평가**: `ko-sroberta-multitask` vs `all-MiniLM-L6-v2` 한국어 발언 데이터에서 성능 비교. 재벡터화 비용 감안하여 결정.

---

## Phase 3 (구독자 기반 확보 후)

- [ ] **Zero-Query 자동 피드**: 매일 밤 전체 발언을 자동 분석하여 "오늘의 모순 발언 TOP 5"를 홈화면에 표시. 주장 추출 파이프라인 + LLM 비용 검토 선행 필요.
- [ ] **발언 타임라인 UI**: 의원별 주제에 대한 입장 변화를 시간 축 위에 시각화. 데이터 구조 설계 및 프론트엔드 컴포넌트 필요.
- [ ] **복수 의원 비교**: "홍길동 vs 이순신" 같은 의원 간 입장 비교 기능.
- [ ] **소셜 공유 버튼**: KakaoTalk, Twitter 직접 공유 버튼. 현재는 URL 복사로 대체.

---

## 기술 부채

- [ ] `except Exception as e` 패턴 정리 (`modules/rag/search_service.py` 포함) — 구체적 예외 타입으로 교체.
- [ ] `modules/load/pdf_to_speech_loader.py:9` TODO 해결 — pdfurl 상태 업데이트 로직 검토.
