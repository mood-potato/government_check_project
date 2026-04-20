import type { HomePageDto } from "./types";

const portraitUrls = [
  "https://lh3.googleusercontent.com/aida-public/AB6AXuBKhWS-cELiEd3l5ow7sK2mt7Hjg9xLAAGZ5H05Uuz31YxBnTl6pLuGpvbe54IP8FMJsDg4xu5tumUBcubucdaZcfuaU_s1t9rqkhAJYoo25_Y4kBDqheeFcw6KXenPcXo6jCsEGo9pOjkIYeK2gCPr_DTzqw5WAIMHV4wbpJLKI8w0-8B-b20GjJwSD0wwoOJpCdymxNFJWCaNXmxSe65JWPY7M7qDWS_PE9sdjZbs0JssN4Y20o9af3sQLX00LyORgJNq-z3XRiRA",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuB-juzB_s8Ge3zW2wqS1lYbK2-cB3yCyKVNf32CeMo2tNOvZTqVos6JZF732O6ybmG0cbb72NCGOEDu4iUgY6LIO4ha_ls6OLXkFEIrerbO7cZvnF0e6EUZZudxjE4oWmJHF2EOWF-cvFssQESuvhW57u0ja_rhYlSaDnd4qS1V9dCufuxBTj8bBXH91il3GnrP4_8cPXnF8GjMRltwUD5WxuRYfjfnypOwi5ZwbR-qMHnshnr5llU5qaYRGWcZrSj5kgyDRjaGiVXp",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuB4zTNrXXWYsWdO-2qLmmi8negyFGnm6QjZvKPu96Ii2M7w0vJbVU2U_0N64CAe7EUEEnwe3tlQOLrr_o_RmF5uPSwRHg30uGStz4nFlAt0q1VJX7hnz6kHXIwW53G41rly7iy-cv10c0XLSKKBh16CvirCWbDEW8z04Eig3cmt5_CoqiXqrlnOa9obmYyU-CMlgY5iSsfbsrtC5KnpiP9yZy039yJdkMMVYkfD8qiCNHujUZi3Nlm2NGY0EeLlUH3DnSAlO099irS0",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuA73lcUCVhLDKwRa1QnJHVR1mtr2Z2O6bfOE3lW1eO0OHQ7DB9REHBVoBDxjx9XN4OU0ubYgtuyDdEtym2hpGu-fOH5yQ5uqMbY-03mti3XayVcgsgHO8uv8zZamrWOn3BW1iWlH89NjUtnY56ZXGlwMPtgKa6G65Hllr26vVDf5Lkg-aQ_U-z4VN1QlfzQsvDbu9Dp7w-SfkeTV1zUwIiX7gg3SqlkjUUz6-ZTRMEjMtxKW8TpEt97lsJBJqC83MlC7gNBt1yS-WLd"
];

export const sampleHomePage: HomePageDto = {
  hero: {
    member: {
      id: "member_123",
      slug: "kim-tae-ho",
      name: "김태호 의원",
      party_name: "대한민국당",
      district_name: "서울 종로구",
      profile_image_url: portraitUrls[0]
    },
    topic_label: "부동산",
    topic_slug: "real-estate",
    past_speech: {
      spoken_date: "2024-02-03",
      meeting_name: "본회의",
      speech_text: "이런 거 아니에요",
      original_url: "https://example.com/speech/1001"
    },
    recent_speech: {
      spoken_date: "2026-02-03",
      meeting_name: "본회의",
      speech_text: "이런 거예요",
      original_url: "https://example.com/speech/2001"
    },
    summary:
      "주택 공급 안정화를 위해 규제 완화가 필수적이라던 2년 전 발언과 달리, 최근 토론회에서는 투기 방지를 위한 강력한 규제 유지를 주장하고 있습니다."
  },
  popular_keywords: [
    { label: "부동산", slug: "real-estate" },
    { label: "교육", slug: "education" },
    { label: "노동", slug: "labor" },
    { label: "의료", slug: "healthcare" },
    { label: "안보", slug: "security" },
    { label: "복지", slug: "welfare" }
  ],
  recent_cases: [
    {
      id: "case_1",
      member: {
        id: "member_201",
        slug: "park-min-su",
        name: "박민수 의원",
        party_name: "예시당",
        district_name: "서울 중구",
        profile_image_url: portraitUrls[1]
      },
      topic_label: "교육정책",
      summary: "입시 제도 개편에 대해 '현행 유지'에서 '전면 개편'으로 입장을 선회했습니다."
    },
    {
      id: "case_2",
      member: {
        id: "member_202",
        slug: "lee-seo-yeon",
        name: "이서연 의원",
        party_name: "예시당",
        district_name: "경기 성남분당갑",
        profile_image_url: portraitUrls[2]
      },
      topic_label: "노동개혁",
      summary: "근로시간 유연화에 대해 기업 입장 대변에서 노동자 권익 보호로 발언 톤이 변화했습니다."
    },
    {
      id: "case_3",
      member: {
        id: "member_203",
        slug: "choi-jun-ho",
        name: "최준호 의원",
        party_name: "예시당",
        district_name: "대구 수성갑",
        profile_image_url: portraitUrls[3]
      },
      topic_label: "에너지 안보",
      summary: "탈원전 기조에서 원전 비중 확대 찬성으로 정책 방향이 달라진 사례입니다."
    }
  ],
  featured_members: [
    {
      rank: 1,
      member: {
        id: "member_301",
        slug: "han-ji-hoon",
        name: "한지훈",
        party_name: "예시당",
        district_name: "부산 해운대갑",
        profile_image_url: portraitUrls[1]
      },
      summary: "언급 이슈: 국민연금 개혁, 저출산 대책"
    },
    {
      rank: 2,
      member: {
        id: "member_302",
        slug: "jung-so-young",
        name: "정소영",
        party_name: "예시당",
        district_name: "강원 춘천갑",
        profile_image_url: portraitUrls[2]
      },
      summary: "언급 이슈: 수도권 집중화, 지방 소멸 방지"
    },
    {
      rank: 3,
      member: {
        id: "member_303",
        slug: "kang-seung-woo",
        name: "강승우",
        party_name: "예시당",
        district_name: "대전 유성갑",
        profile_image_url: portraitUrls[3]
      },
      summary: "언급 이슈: 반도체 특별법, 신산업 규제"
    }
  ],
  disclaimer: "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."
};
