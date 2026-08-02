# _workspace/ 산출물은 git에 커밋한다

`dev-process-orchestrator`의 7단계는 각 단계 산출물을 `_workspace/01_flow_create.md` ~ `07_review_log.md`로 저장한다. `notion-save` 스킬로 Notion에도 올릴 수 있지만, Notion 접근 권한이 없는 팀원도 저장소를 clone하는 것만으로 진행 중인 설계 문서를 볼 수 있어야 하므로 `_workspace/`는 `.gitignore`에 넣지 않고 그대로 커밋한다. 단점은 반복 초안 작업이 diff 노이즈를 늘린다는 것이지만, git이 유일한 공유 소스가 되는 이점이 더 크다고 판단했다.
