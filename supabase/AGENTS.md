# Supabase Directory Notes

이 디렉터리는 Supabase CLI 프로젝트 설정, DB 마이그레이션, seed 데이터를 관리한다.
GitHub 원격 저장소와 Supabase 원격 프로젝트는 별개다. `git push`는 코드 저장소에만
반영되며, Supabase DB 스키마나 데이터에는 자동 반영되지 않는다.

## Linked Project

- Supabase project: `government_check_project`
- Project ref: `rmotcqoajmhejxxilbex`
- Current branch: `main`

## File Roles

- `config.toml`: 로컬 Supabase 설정, 로컬 포트, migration/seed 설정을 관리한다.
- `migrations/`: 로컬 또는 원격 Supabase DB에 적용할 스키마 변경 파일을 둔다.
- `seed.sql`: 18대-22대 국회의원 기본정보 1609건을 `speakers` 테이블에 넣는 seed 파일이다.
- `.temp/`, `.branches/`: Supabase CLI가 관리하는 로컬 메타데이터다. 직접 수정하지 않는다.

## Data Direction

- `speakers`는 국회의원 마스터 테이블이다.
- `seed.sql`은 `mona_code + assembly_number` 기준으로 upsert되도록 생성되어 있다.
- 비국회의원 발언자는 `speakers`에 억지로 넣지 않는다.
- 비국회의원 발언자는 `speeches` 쪽 원문 발언자 필드에 보존하는 방향으로 관리한다.
- 의원 상세/의원 통계는 `speakers`에 매칭된 발언을 기준으로 하고, 회의 상세/검색은
  비국회의원 발언도 포함할 수 있어야 한다.

## Safe Workflow

- 원격 반영 전에는 `supabase db push --dry-run`으로 먼저 적용 내용을 확인한다.
- seed 반영은 운영 DB 데이터에 영향을 줄 수 있으므로 dry-run과 백업 확인 후 진행한다.
- DB 비밀번호, API key, service role key 같은 민감한 값은 이 문서나 commit에 넣지 않는다.
- `supabase/seed.sql` 재생성은 repo root에서 다음 명령으로 한다.

```bash
.venv/bin/python -m pipelines.speaker_seed
```
