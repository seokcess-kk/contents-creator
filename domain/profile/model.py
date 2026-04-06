"""클라이언트 프로필 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ServiceItem(BaseModel):
    """주요 서비스/시술 항목."""

    name: str
    description: str = ""


class ReviewItem(BaseModel):
    """고객 후기 항목."""

    text: str
    source: str = ""


class ClientProfile(BaseModel):
    """클라이언트 프로필. Level 1(필수) + Level 2(방향성)."""

    id: str = ""

    # Level 1: 기본 정보 (필수)
    company_name: str = ""
    representative: str = ""  # 대표자/원장명
    industry: str = ""  # 의료, 뷰티, 건강
    sub_category: str = ""  # 한의원, 피부과, 치과 등
    region: str = ""  # 시/구 단위
    services: list[ServiceItem] = Field(default_factory=list)

    # Level 2: 콘텐츠 방향성
    tone_and_manner: str = ""  # 전문가형/친근형/스토리텔링형
    target_persona: str = ""  # 수동 입력
    usp: str = ""  # 한 줄 핵심 차별점
    frequent_expressions: list[str] = Field(default_factory=list)
    prohibited_expressions: list[str] = Field(default_factory=list)  # 반드시 수동 입력

    # Level 3: 연락처/후기
    phone: str = ""
    address: str = ""
    reviews: list[ReviewItem] = Field(default_factory=list)

    # 사진
    photo_path: str = ""  # 원장/대표 사진 로컬 경로

    # 메타
    source_url: str = ""
    status: str = "draft"  # draft | confirmed
    confidence_scores: dict[str, str] = Field(default_factory=dict)  # 필드별 신뢰도

    def is_medical(self) -> bool:
        """의료 업종인지 판단한다."""
        medical_keywords = {"의료", "한의원", "피부과", "치과", "병원", "의원", "클리닉", "성형"}
        return any(k in self.industry for k in medical_keywords) or any(
            k in self.sub_category for k in medical_keywords
        )
