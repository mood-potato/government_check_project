import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="발언 검색", layout="wide")
st.title("국회 발언 시맨틱 검색")

# 검색 상태 초기화
if "search_results" not in st.session_state:
    st.session_state.search_results = []


@st.cache_resource
def get_search_service():
    """검색 서비스 초기화 (캐싱)"""
    try:
        from modules.utils.db_connections import get_qdrant_client
        from modules.rag.search_service import SpeechSearchService

        client = get_qdrant_client()
        return SpeechSearchService(qdrant_client=client)
    except Exception as e:
        st.error(f"검색 서비스 초기화 실패: {e}")
        return None


def main():
    # 사이드바 필터
    st.sidebar.header("검색 필터")
    top_k = st.sidebar.slider("검색 결과 수", min_value=5, max_value=50, value=10)
    score_threshold = st.sidebar.slider(
        "최소 유사도", min_value=0.0, max_value=1.0, value=0.3, step=0.05
    )

    speaker_filter = st.sidebar.text_input("발언자 필터 (선택)", placeholder="예: 의장 홍길동")
    date_filter = st.sidebar.text_input("날짜 필터 (선택)", placeholder="예: 2024-01-15")

    # 검색 입력
    query = st.text_input(
        "검색어를 입력하세요",
        placeholder="예: 예산 심의, 교육 정책, 환경 문제...",
        key="search_query",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        search_button = st.button("검색", type="primary", use_container_width=True)

    # 검색 실행
    if search_button and query:
        search_service = get_search_service()

        if search_service is None:
            st.error("검색 서비스를 사용할 수 없습니다. Qdrant 연결을 확인하세요.")
            return

        with st.spinner("검색 중..."):
            results = search_service.search(
                query=query,
                top_k=top_k,
                speaker=speaker_filter if speaker_filter else None,
                date=date_filter if date_filter else None,
                score_threshold=score_threshold,
            )
            st.session_state.search_results = results

    # 결과 표시
    results = st.session_state.search_results

    if results:
        st.subheader(f"검색 결과: {len(results)}건")

        for i, result in enumerate(results, 1):
            score_pct = result["score"] * 100
            score_color = "green" if score_pct >= 70 else "orange" if score_pct >= 50 else "red"

            with st.expander(
                f"#{i} [{result['speaker']}] {result['title'][:50]}... (유사도: {score_pct:.1f}%)",
                expanded=(i <= 3),
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("유사도", f"{score_pct:.1f}%")
                with col2:
                    st.metric("발언자", result["speaker"])
                with col3:
                    st.metric("날짜", result["date"])

                st.markdown("**회의:**")
                st.caption(result["title"])

                st.markdown("**발언 내용:**")
                text = result["text"]
                if len(text) > 500:
                    st.write(text[:500] + "...")
                    with st.expander("전체 보기"):
                        st.write(text)
                else:
                    st.write(text)

    elif query and search_button:
        st.info("검색 결과가 없습니다. 다른 검색어를 시도해보세요.")

    # 사용 안내
    with st.sidebar.expander("사용 안내"):
        st.markdown(
            """
        **시맨틱 검색**은 키워드 일치가 아닌
        의미적 유사성을 기반으로 검색합니다.

        예시 검색어:
        - "예산 심의 관련 발언"
        - "환경 보호 정책"
        - "교육 개혁 방안"

        **필터 사용:**
        - 발언자: 특정 의원 발언만 검색
        - 날짜: 특정 회의 발언만 검색
        """
        )


if __name__ == "__main__":
    main()
