# IDNT (아이덴트) - Configuration
# ---------------------------------------------------------------
# Environment variables are loaded from .env or system environment.
# Copy .env.example to .env and fill in production values.
# ---------------------------------------------------------------

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────
    app_name: str = "IDNT"
    app_version: str = "1.0.0"
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Database ─────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://idnt:idnt@localhost:5432/idnt",
        description="Async PostgreSQL connection string",
    )

    # ── AWS / S3 ─────────────────────────────────────────────────
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    s3_bucket: str = "idnt-cards"
    s3_prefix: str = "cards/"

    # ── JWT / Auth ───────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # ── Face Processing ──────────────────────────────────────────
    face_min_resolution: int = 300
    face_quality_threshold: float = 0.6
    face_similarity_threshold: float = 0.45
    insightface_model: str = "buffalo_l"

    # ── Card Design ──────────────────────────────────────────────
    card_width: int = 1012
    card_height: int = 638
    card_bg_color: str = "#111111"
    card_photo_diameter: int = 200
    card_validity_years: int = 2
    card_font_family: str = "Pretendard"
    card_font_fallbacks: list[str] = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    # ── Apple Wallet ─────────────────────────────────────────────
    apple_team_id: str = ""
    apple_pass_type_id: str = "pass.com.idnt.employee"
    apple_organization_name: str = "IDNT"
    apple_cert_path: str = ""
    apple_key_path: str = ""
    apple_wwdr_cert_path: str = ""

    # ── Google Wallet ────────────────────────────────────────────
    google_issuer_id: str = ""
    google_service_account_json: str = ""

    model_config = {"env_prefix": "IDNT_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
