"""프로젝트 설정 관리. .env에서 환경 변수를 로드한다."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_env() -> None:
    env_path = PROJECT_ROOT / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)


_load_env()


class Settings(BaseModel):
    """환경 변수 기반 설정."""

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Google Gemini (VLM)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # Naver
    naver_client_id: str = os.getenv("NAVER_CLIENT_ID", "")
    naver_client_secret: str = os.getenv("NAVER_CLIENT_SECRET", "")

    # Paths
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "output"
    workspace_dir: Path = PROJECT_ROOT / "_workspace"


settings = Settings()
