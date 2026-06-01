import type { MemberDetailPageDto } from "./types";

const portraitUrls = [
  "https://lh3.googleusercontent.com/aida-public/AB6AXuC3FZ-gnurV-2B_39GtGyRP5kP_uq9LmxTuoPERO8ah6GOsyA5M6Iulv8NJabUkK_vZwqwuGxV2lUrQ6PDf6TY1xumsp3UXGIv103-nc2szRoDiUwQbFTCzUOpLmAUF9gMfN45Oh4DjLz6b8mFZoR3UHXUQe9Iv1BzbAvhGqOE4J5pjjz6jnlZaq1b3YFpQDfC5ffuO8ZyCPgldY8cuBEQC5nC4pCFNos-eDu2Qw5h0-6Ejqh99MrXeHo7CqVb-TH32vI-BLHv8u78f",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDTdm0L_uU0Xa68_KD2gPWkAP6OVBfGDIy96kM9WNw969716n73-TuLJMGlK2Rrsor7uQToZlAx5-xvGHqOnxJtQcpqxsD-i5xBjHSACHnTZjZh7w9X_SDqP9W0CnmDw8V9u0OtNPLTUAOPfRnO_3QALnmgsHHhRjuXPSSo6KcvJvbEZH0DUAMVdIaeW3A8ibMBivk2n0SJOqrcNlq0A3XewViPrje4RdkUG34VoIaZG_fNEj0gUyfqBO9EFOqHtvgFYyDOKYJU3aOU",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuBGI6e6O7tOt9BCM6uIbzjFrcplwBK3cMFA1XnfHLyIPY8Y6WVF5DgqOTkZfE3clHKPGjXRU-8Xp6291bvJHOhUqhme2oTVzunPdfFXLqywfwLrL1Mt7tIm-_gxylCIiFH9mbgWWanyy8dT7nRBWo-5MpYLBPVVMC__30zdnlGtp6N7MgWRZeuCt19eM6EGTOM0Brco6H7E8mcJmHJ1y6Iew3_5c2BRfMjHvMBx70lzwYYNn0xQ4UbntiAhHumeCcWlY8m3tk-wny3k",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCNQcfveeyTiMninfKDnHsWwYGVORyQAchkAlpQqnmmcGSZ-_1MFppgzkRE3uKPqv7ji9gSCCQz2ob2-CcAXq8cGl9zyJYhb0XDOvTlgYX_iYEhTNp60geMeBE9PnERM1OPIRE_nkVMHQ5wEPPXhUL8bfBpZ_hEfWKIGnj4xPQy7AISpexLMIrxKF_0TieUeaUdUijFrrB-yJzXKxAaLw4Ph0YnY6XREgFkRCV1c-Sg7C58tJ7iUbjMeko_5_bMYJvJlF1mokAR5l1o"
];

export const sampleMemberDetailPage: MemberDetailPageDto = {
  member: {
    id: "member_401",
    slug: "kim-seo-jun",
    name: "김서준 의원",
    party_name: "더불어행복당",
    district_name: "서울 마포구 갑",
    committee_name: "기획재정위원회",
    generation_label: "제22대 국회의원",
    status_label: "Active Member",
    fact_summary: "최근 2년간 부동산·노동 쟁점 회의에 반복적으로 참여한 의원",
    profile_image_url: portraitUrls[0]
  },
  metrics: [
    { label: "자주 등장한 쟁점", value: "부동산 취득세", tone: "primary" },
    { label: "참여 회의 수", value: "142", supporting_text: "건" },
    { label: "상반 발언 후보", value: "12", supporting_text: "건", tone: "tertiary" },
    { label: "최근 발언 시점", value: "2일 전", supporting_text: "14:30" }
  ],
  conflicts: [
    {
      id: "conflict_1",
      topic_label: "노동법 개정안",
      date: "2024.11.12",
      meeting_name: "기획재정위원회 제3차 회의",
      opponent_name: "이영호 의원",
      opponent_detail: "국민의힘",
      quote: "노동자의 유연한 권리 보장이 우선되지 않는다면 경제 활성화는 허상입니다."
    },
    {
      id: "conflict_2",
      topic_label: "종부세 완화",
      date: "2024.10.05",
      meeting_name: "본회의 정기국회",
      opponent_name: "박지현 장관",
      opponent_detail: null,
      quote: "세수 확보라는 명목 하에 중산층의 부담을 가중시키는 처사입니다."
    },
    {
      id: "conflict_3",
      topic_label: "R&D 예산",
      date: "2024.09.21",
      meeting_name: "예산결산특별위원회",
      opponent_name: "김민석 의원",
      opponent_detail: "무소속",
      quote: "미래 동력을 깎아먹는 예산 삭감은 국가적 자살 행위와 다름없습니다."
    }
  ],
  contradictory_speeches: [
    {
      label: "2024년 1월 발언",
      speech_text: "주택 담보 대출 규제는 시장 안정을 위해 유지되어야 하며, 인위적인 완화는 투기 심리만 자극할 뿐입니다.",
      source: "기획재정위원회 제1차 회의록 중",
      tone: "past"
    },
    {
      label: "2026년 3월 발언",
      speech_text: "지나친 대출 규제가 실수요자의 주거 사다리를 걷어차고 있습니다. 이제는 과감한 규제 혁파가 필요한 시점입니다.",
      source: "경제 활성화 대책 공청회 중",
      tone: "recent"
    }
  ],
  recent_speeches: [
    {
      id: "speech_latest",
      spoken_date: "2026-04-24",
      meeting_name: "제434회 제2차 본회의",
      speech_text: "국민이 체감할 수 있는 정책 집행이 필요합니다.",
      original_url: "https://record.assembly.go.kr/conf/latest"
    }
  ],
  agendas: [
    {
      id: "agenda_1",
      title: "탄소 중립 실천 촉진법",
      meeting_count: 8,
      recent_date: "2024.11.01",
      summary: "실질적인 탄소 배출 감소를 위한 인센티브 구조 도입을 지속적으로 강조함."
    },
    {
      id: "agenda_2",
      title: "반도체 산업 지원 특별법",
      meeting_count: 15,
      recent_date: "2024.10.15",
      summary: "글로벌 경쟁력 확보를 위한 세액 공제 혜택 확대를 주된 논리로 내세움."
    },
    {
      id: "agenda_3",
      title: "청년 일자리 매칭 플랫폼 구축",
      meeting_count: 4,
      recent_date: "2024.08.30",
      summary: "단순 지원금보다는 민관 협력을 통한 지속 가능한 일자리 생태계 조성을 주장함."
    },
    {
      id: "agenda_4",
      title: "디지털 자산 투자자 보호법",
      meeting_count: 11,
      recent_date: "2024.11.10",
      summary: "거래소의 투명성 강화와 투자자 교육 프로그램 의무화를 제안함."
    }
  ],
  similar_members: [
    {
      member: {
        id: "member_501",
        slug: "jung-min-ho",
        name: "정민호 의원",
        party_name: "더불어행복당",
        district_name: "경기 고양갑",
        profile_image_url: portraitUrls[1]
      },
      basis: "부동산 세제, 신산업 규제 완화",
      value_label: "84%"
    },
    {
      member: {
        id: "member_502",
        slug: "han-ye-seul",
        name: "한예슬 의원",
        party_name: "더불어행복당",
        district_name: "서울 강남을",
        profile_image_url: portraitUrls[2]
      },
      basis: "금융 소비자 보호, 탄소 중립",
      value_label: "76%"
    }
  ],
  opposing_members: [
    {
      member: {
        id: "member_601",
        slug: "lee-young-ho",
        name: "이영호 의원",
        party_name: "국민의힘",
        district_name: "부산 남구갑",
        profile_image_url: portraitUrls[3]
      },
      basis: "노동 유연성 vs 보호 강화",
      value_label: "24회"
    },
    {
      member: {
        id: "member_602",
        slug: "kim-ji-su",
        name: "김지수 의원",
        party_name: "국민의힘",
        district_name: "인천 연수을",
        profile_image_url: portraitUrls[2]
      },
      basis: "교육 재산 배분, 복지 확대",
      value_label: "18회"
    }
  ],
  disclaimer: "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."
};
