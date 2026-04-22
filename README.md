# goverment_check_project
국회의원 회의록 분석 확인하는 웹사이트


## Docker

```bash
make up
make logs
make down
```

- 백엔드: `docker/backend.Dockerfile`
- 프론트엔드: `docker/frontend.Dockerfile`
- 파이프라인: `docker/pipeline.Dockerfile`

파이프라인은 필요할 때만 실행합니다.

```bash
make pipeline
```
