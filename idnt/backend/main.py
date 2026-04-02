# IDNT (아이덴트) - FastAPI Backend
# ---------------------------------------------------------------
# Install dependencies:
#   pip install -r requirements.txt
#
# Run the server:
#   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
#
# Or directly:
#   python main.py
#
# Ensure PostgreSQL is running with pgvector extension:
#   CREATE EXTENSION IF NOT EXISTS vector;
#
# Environment variables (or .env file):
#   IDNT_DATABASE_URL=postgresql+asyncpg://idnt:idnt@localhost:5432/idnt
#   IDNT_JWT_SECRET=your-secret-key
#   IDNT_AWS_ACCESS_KEY_ID=...
#   IDNT_AWS_SECRET_ACCESS_KEY=...
# ---------------------------------------------------------------

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import AccessLog, Base, CardStatus, Employee, FaceEmbedding, IDCard

# ── Logging ─────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("idnt.main")

# ── Database engine ─────────────────────────────────────────────

engine = create_async_engine(settings.database_url, echo=settings.debug, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency that yields a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


DB = Annotated[AsyncSession, Depends(get_db)]

# ── FastAPI App ─────────────────────────────────────────────────

app = FastAPI(
    title="IDNT API",
    description="아이덴트 디지털 사원증 발급 시스템 백엔드",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic Schemas ───────────────────────────────────────────

class CaptureRequest(BaseModel):
    employee_number: str
    name: str
    department: str
    position: str
    email: str


class CaptureResponse(BaseModel):
    card_id: str
    employee_id: str
    status: str
    card_image_url: str | None = None
    pkpass_url: str | None = None
    google_pass_url: str | None = None
    quality_score: float
    message: str


class VerifyRequest(BaseModel):
    employee_id: str


class VerifyResponse(BaseModel):
    verified: bool
    similarity: float
    employee_id: str | None = None
    message: str


class CardStatusResponse(BaseModel):
    card_id: str
    employee_id: str
    employee_name: str
    status: str
    card_image_url: str | None
    pkpass_url: str | None
    google_pass_url: str | None
    issued_at: str
    expires_at: str | None


class DashboardResponse(BaseModel):
    today_issued: int
    processing: int
    active: int
    failed: int
    total_employees: int


class FailureItem(BaseModel):
    card_id: str
    employee_id: str
    employee_name: str
    employee_number: str
    status: str
    issued_at: str


class FailureListResponse(BaseModel):
    failures: list[FailureItem]
    total: int


class DeactivateResponse(BaseModel):
    card_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


# ── Startup / Shutdown ─────────────────────────────────────────


@app.on_event("startup")
async def on_startup() -> None:
    """Create database tables and warm up ML models on startup."""
    logger.info("Starting IDNT backend v%s", settings.app_version)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Dispose of the engine connection pool."""
    await engine.dispose()
    logger.info("Database engine disposed")


# ── Health Check ────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "version": settings.app_version}


# ── POST /api/v1/capture ───────────────────────────────────────


@app.post(
    "/api/v1/capture",
    response_model=CaptureResponse,
    tags=["cards"],
    summary="Capture face and issue ID card",
)
async def capture_face(
    db: DB,
    photo: UploadFile = File(..., description="Face photo (JPEG/PNG)"),
    employee_number: str = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    position: str = Form(...),
    email: str = Form(...),
) -> CaptureResponse:
    """Full pipeline: quality check, background removal, embedding, card render, wallet pass.

    Accepts multipart/form-data with a photo file and employee fields.
    """
    from face_processor import (
        check_duplicate_identity,
        face_quality_check,
        generate_face_embedding,
        remove_background,
    )
    from card_renderer import render_id_card
    from wallet_generator import generate_pkpass, generate_google_wallet_jwt

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="사진 파일이 비어있습니다")

    # ── Step 1: Quality check ────────────────────────────────────
    quality = await face_quality_check(image_bytes)
    if not quality.passed:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "quality_check_failed",
                "score": quality.score,
                "reasons": quality.reasons,
                "messages": quality.messages,
            },
        )

    # ── Step 2: Generate embedding ───────────────────────────────
    embedding = await generate_face_embedding(image_bytes)

    # ── Step 3: Duplicate check ──────────────────────────────────
    is_dup, dup_employee_id = await check_duplicate_identity(embedding, db)
    if is_dup:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_identity",
                "message": "이미 등록된 얼굴입니다. HR팀에 문의하세요",
                "existing_employee_id": dup_employee_id,
            },
        )

    # ── Step 4: Remove background ────────────────────────────────
    clean_photo = await remove_background(image_bytes)

    # ── Step 5: Get or create employee ───────────────────────────
    result = await db.execute(
        select(Employee).where(Employee.employee_number == employee_number)
    )
    employee = result.scalar_one_or_none()

    if employee is None:
        employee = Employee(
            employee_number=employee_number,
            name=name,
            department=department,
            position=position,
            email=email,
        )
        db.add(employee)
        await db.flush()

    # ── Step 6: Save embedding ───────────────────────────────────
    face_emb = FaceEmbedding(employee_id=employee.id, embedding=embedding.tolist())
    db.add(face_emb)

    # ── Step 7: Render card ──────────────────────────────────────
    expires_at = datetime.now(timezone.utc) + timedelta(days=365 * settings.card_validity_years)
    employee_data = {
        "employee_number": employee_number,
        "name": name,
        "department": department,
        "position": position,
        "email": email,
        "expires_at": expires_at,
    }
    card_image_bytes = await render_id_card(clean_photo, employee_data)

    # ── Step 8: Create card record ───────────────────────────────
    card = IDCard(
        employee_id=employee.id,
        status=CardStatus.active,
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db.add(card)
    await db.flush()

    # ── Step 9: Upload to S3 (best-effort) ───────────────────────
    card_image_url = None
    pkpass_url = None
    google_pass_url = None

    try:
        import boto3

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region,
        )
        card_key = f"{settings.s3_prefix}{card.id}.png"
        s3.put_object(
            Bucket=settings.s3_bucket,
            Key=card_key,
            Body=card_image_bytes,
            ContentType="image/png",
        )
        card_image_url = f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{card_key}"
    except Exception as exc:
        logger.warning("S3 upload failed (card image): %s", exc)

    # ── Step 10: Generate wallet passes (best-effort) ────────────
    try:
        pkpass_bytes = await generate_pkpass(card_image_bytes, employee_data)
        if pkpass_bytes and settings.aws_access_key_id:
            pkpass_key = f"{settings.s3_prefix}{card.id}.pkpass"
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=pkpass_key,
                Body=pkpass_bytes,
                ContentType="application/vnd.apple.pkpass",
            )
            pkpass_url = f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{pkpass_key}"
    except Exception as exc:
        logger.warning("Apple Wallet pass generation failed: %s", exc)

    try:
        google_pass_url = await generate_google_wallet_jwt(card_image_bytes, employee_data)
    except Exception as exc:
        logger.warning("Google Wallet pass generation failed: %s", exc)

    # ── Step 11: Update card record ──────────────────────────────
    card.card_image_url = card_image_url
    card.pkpass_url = pkpass_url
    card.google_pass_url = google_pass_url

    # ── Step 12: Audit log ───────────────────────────────────────
    db.add(AccessLog(
        employee_id=employee.id,
        card_id=card.id,
        action="card_issued",
    ))

    await db.commit()

    return CaptureResponse(
        card_id=str(card.id),
        employee_id=str(employee.id),
        status=card.status.value,
        card_image_url=card_image_url,
        pkpass_url=pkpass_url,
        google_pass_url=google_pass_url,
        quality_score=quality.score,
        message="사원증이 성공적으로 발급되었습니다",
    )


# ── POST /api/v1/verify ───────────────────────────────────────


@app.post(
    "/api/v1/verify",
    response_model=VerifyResponse,
    tags=["verification"],
    summary="Verify face against existing embedding",
)
async def verify_face(
    db: DB,
    photo: UploadFile = File(..., description="Face photo to verify"),
    employee_id: str = Form(..., description="Employee UUID to verify against"),
) -> VerifyResponse:
    """Verify that a captured face matches the stored embedding for an employee."""
    import numpy as np
    from face_processor import generate_face_embedding

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="사진 파일이 비어있습니다")

    # Generate embedding from the new photo
    try:
        new_embedding = await generate_face_embedding(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Fetch stored embedding
    emp_uuid = uuid.UUID(employee_id)
    result = await db.execute(
        select(FaceEmbedding)
        .where(FaceEmbedding.employee_id == emp_uuid)
        .order_by(FaceEmbedding.created_at.desc())
        .limit(1)
    )
    stored = result.scalar_one_or_none()
    if stored is None:
        raise HTTPException(status_code=404, detail="등록된 얼굴 정보가 없습니다")

    # Cosine similarity
    stored_emb = np.array(stored.embedding, dtype=np.float32)
    similarity = float(np.dot(new_embedding, stored_emb) / (
        np.linalg.norm(new_embedding) * np.linalg.norm(stored_emb) + 1e-8
    ))
    verified = similarity >= (1 - settings.face_similarity_threshold)

    # Audit log
    db.add(AccessLog(
        employee_id=emp_uuid,
        action="face_verified" if verified else "face_verification_failed",
    ))
    await db.commit()

    return VerifyResponse(
        verified=verified,
        similarity=round(similarity, 4),
        employee_id=employee_id if verified else None,
        message="본인 확인 완료" if verified else "본인 확인에 실패했습니다. 다시 시도해주세요",
    )


# ── GET /api/v1/cards/{employee_id} ───────────────────────────


@app.get(
    "/api/v1/cards/{employee_id}",
    response_model=CardStatusResponse,
    tags=["cards"],
    summary="Get card status for an employee",
)
async def get_card_status(employee_id: str, db: DB) -> CardStatusResponse:
    """Return the most recent card for the given employee."""
    emp_uuid = uuid.UUID(employee_id)

    result = await db.execute(
        select(IDCard, Employee)
        .join(Employee, IDCard.employee_id == Employee.id)
        .where(IDCard.employee_id == emp_uuid)
        .order_by(IDCard.issued_at.desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="발급된 사원증이 없습니다")

    card, employee = row
    return CardStatusResponse(
        card_id=str(card.id),
        employee_id=str(employee.id),
        employee_name=employee.name,
        status=card.status.value,
        card_image_url=card.card_image_url,
        pkpass_url=card.pkpass_url,
        google_pass_url=card.google_pass_url,
        issued_at=card.issued_at.isoformat(),
        expires_at=card.expires_at.isoformat() if card.expires_at else None,
    )


# ── GET /api/v1/admin/dashboard ───────────────────────────────


@app.get(
    "/api/v1/admin/dashboard",
    response_model=DashboardResponse,
    tags=["admin"],
    summary="Dashboard statistics",
)
async def admin_dashboard(db: DB) -> DashboardResponse:
    """Return aggregate statistics for the admin dashboard."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's issued cards
    today_issued = await db.scalar(
        select(func.count(IDCard.id)).where(
            IDCard.issued_at >= today_start,
            IDCard.status == CardStatus.active,
        )
    ) or 0

    # Processing
    processing = await db.scalar(
        select(func.count(IDCard.id)).where(IDCard.status == CardStatus.processing)
    ) or 0

    # Active
    active = await db.scalar(
        select(func.count(IDCard.id)).where(IDCard.status == CardStatus.active)
    ) or 0

    # Failed (deactivated or expired)
    failed = await db.scalar(
        select(func.count(IDCard.id)).where(
            IDCard.status.in_([CardStatus.deactivated, CardStatus.expired])
        )
    ) or 0

    # Total employees
    total_employees = await db.scalar(select(func.count(Employee.id))) or 0

    return DashboardResponse(
        today_issued=today_issued,
        processing=processing,
        active=active,
        failed=failed,
        total_employees=total_employees,
    )


# ── GET /api/v1/admin/failures ────────────────────────────────


@app.get(
    "/api/v1/admin/failures",
    response_model=FailureListResponse,
    tags=["admin"],
    summary="List failed / deactivated cards",
)
async def admin_failures(
    db: DB,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> FailureListResponse:
    """Return cards that are deactivated or expired."""
    stmt = (
        select(IDCard, Employee)
        .join(Employee, IDCard.employee_id == Employee.id)
        .where(IDCard.status.in_([CardStatus.deactivated, CardStatus.expired]))
        .order_by(IDCard.issued_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    total = await db.scalar(
        select(func.count(IDCard.id)).where(
            IDCard.status.in_([CardStatus.deactivated, CardStatus.expired])
        )
    ) or 0

    failures = [
        FailureItem(
            card_id=str(card.id),
            employee_id=str(emp.id),
            employee_name=emp.name,
            employee_number=emp.employee_number,
            status=card.status.value,
            issued_at=card.issued_at.isoformat(),
        )
        for card, emp in rows
    ]

    return FailureListResponse(failures=failures, total=total)


# ── POST /api/v1/admin/cards/{card_id}/deactivate ─────────────


@app.post(
    "/api/v1/admin/cards/{card_id}/deactivate",
    response_model=DeactivateResponse,
    tags=["admin"],
    summary="Deactivate a card",
)
async def deactivate_card(card_id: str, db: DB) -> DeactivateResponse:
    """Mark a card as deactivated."""
    card_uuid = uuid.UUID(card_id)

    result = await db.execute(select(IDCard).where(IDCard.id == card_uuid))
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="사원증을 찾을 수 없습니다")

    if card.status == CardStatus.deactivated:
        raise HTTPException(status_code=409, detail="이미 비활성화된 사원증입니다")

    card.status = CardStatus.deactivated

    db.add(AccessLog(
        employee_id=card.employee_id,
        card_id=card.id,
        action="card_deactivated",
    ))
    await db.commit()

    return DeactivateResponse(
        card_id=str(card.id),
        status=card.status.value,
        message="사원증이 비활성화되었습니다",
    )


# ── GET /api/v1/admin/export ──────────────────────────────────


@app.get(
    "/api/v1/admin/export",
    tags=["admin"],
    summary="Export all cards as CSV",
)
async def export_csv(db: DB) -> StreamingResponse:
    """Export all issued cards as a CSV file."""
    stmt = (
        select(IDCard, Employee)
        .join(Employee, IDCard.employee_id == Employee.id)
        .order_by(IDCard.issued_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "card_id", "employee_number", "name", "department", "position",
        "email", "status", "issued_at", "expires_at",
    ])

    for card, emp in rows:
        writer.writerow([
            str(card.id),
            emp.employee_number,
            emp.name,
            emp.department,
            emp.position,
            emp.email,
            card.status.value,
            card.issued_at.isoformat(),
            card.expires_at.isoformat() if card.expires_at else "",
        ])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="idnt_cards_{timestamp}.csv"'},
    )


# ── Global exception handler ──────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Convert ValueErrors into 422 responses."""
    return HTTPException(status_code=422, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Catch-all for unexpected errors."""
    logger.exception("Unhandled exception: %s", exc)
    raise HTTPException(
        status_code=500,
        detail="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
    )


# ── Entrypoint ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
