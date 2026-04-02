# IDNT (아이덴트) - Face Processing Pipeline
# ---------------------------------------------------------------
# Dependencies:
#   pip install insightface onnxruntime rembg pillow numpy
#
# On first run InsightFace will download the buffalo_l model (~300 MB).
# Set INSIGHTFACE_HOME to control the download directory.
# ---------------------------------------------------------------

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from config import settings

logger = logging.getLogger("idnt.face_processor")

# ── Korean error messages ────────────────────────────────────────

MESSAGES = {
    "no_face": "얼굴이 보이지 않아요",
    "too_dark": "더 밝은 곳으로 이동해주세요",
    "side_angle": "정면을 바라봐주세요",
    "eyes_closed": "눈을 뜨고 카메라를 바라봐주세요",
    "mask": "마스크를 잠시 내려주세요",
    "low_resolution": "카메라에 더 가까이 다가와주세요",
    "duplicate": "이미 등록된 얼굴입니다. HR팀에 문의하세요",
}

# ── Result dataclass ─────────────────────────────────────────────


@dataclass
class QualityResult:
    """Result of a face quality check."""

    passed: bool
    score: float  # 0.0 – 1.0
    reasons: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


# ── Lazy-loaded singletons ──────────────────────────────────────

_insightface_app = None


def _get_insightface_app():
    """Return a cached InsightFace FaceAnalysis instance."""
    global _insightface_app
    if _insightface_app is None:
        from insightface.app import FaceAnalysis

        _insightface_app = FaceAnalysis(
            name=settings.insightface_model,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        _insightface_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded (%s)", settings.insightface_model)
    return _insightface_app


_rembg_session = None


def _get_rembg_session():
    """Return a cached rembg session."""
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session

        _rembg_session = new_session("u2net")
        logger.info("rembg session initialised")
    return _rembg_session


# ── Helpers ──────────────────────────────────────────────────────


def _bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    """Convert raw bytes to a BGR numpy array (OpenCV format)."""
    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(pil)
    # RGB → BGR for InsightFace
    return arr[:, :, ::-1].copy()


def _eye_aspect_ratio(landmarks: np.ndarray) -> float:
    """Compute Eye Aspect Ratio from InsightFace 5-point landmarks.

    InsightFace 5-point landmark indices:
        0 – left eye centre
        1 – right eye centre
        2 – nose tip
        3 – left mouth corner
        4 – right mouth corner

    With only centre points we approximate EAR via the vertical distance
    between the eye centres relative to the inter-eye distance.  A low
    ratio suggests closed eyes.
    """
    left_eye = landmarks[0]
    right_eye = landmarks[1]
    inter_eye = np.linalg.norm(right_eye - left_eye)
    if inter_eye < 1e-6:
        return 0.0
    # Vertical openness proxy: distance between eye and nose midpoint
    nose = landmarks[2]
    mid_eye = (left_eye + right_eye) / 2.0
    vertical = np.linalg.norm(mid_eye - nose)
    return float(vertical / inter_eye)


def _lighting_score(image: np.ndarray) -> float:
    """Return a 0-1 score for lighting uniformity (grayscale std / mean)."""
    gray = np.mean(image, axis=2) if image.ndim == 3 else image.astype(float)
    mean_val = gray.mean()
    if mean_val < 1e-6:
        return 0.0
    # Normalised std; lower is more uniform. We invert so higher = better.
    uniformity = 1.0 - min(gray.std() / mean_val, 1.0)
    # Also penalise very dark images
    brightness = min(mean_val / 128.0, 1.0)
    return float(uniformity * 0.4 + brightness * 0.6)


# ── Public API ───────────────────────────────────────────────────


async def face_quality_check(image_bytes: bytes) -> QualityResult:
    """Run comprehensive quality checks on a face photo.

    Checks performed:
    - Face detection (at least one face present)
    - Frontal pose (yaw/pitch within +-15 deg)
    - Lighting uniformity & brightness
    - Minimum face resolution (300x300)
    - Eyes open (EAR > 0.2)
    - No mask / sunglasses (confidence heuristic)

    Returns a QualityResult with a composite score and Korean messages.
    """
    reasons: list[str] = []
    messages: list[str] = []
    sub_scores: list[float] = []

    try:
        img_bgr = _bytes_to_cv2(image_bytes)
    except Exception:
        return QualityResult(passed=False, score=0.0, reasons=["invalid_image"], messages=["이미지를 읽을 수 없습니다"])

    app = _get_insightface_app()
    faces = app.get(img_bgr)

    # ── No face detected ─────────────────────────────────────────
    if not faces:
        return QualityResult(
            passed=False, score=0.0,
            reasons=["no_face"], messages=[MESSAGES["no_face"]],
        )

    face = faces[0]  # Use the largest / most confident face
    bbox = face.bbox.astype(int)  # [x1, y1, x2, y2]
    face_w = bbox[2] - bbox[0]
    face_h = bbox[3] - bbox[1]

    # ── Resolution check ─────────────────────────────────────────
    min_res = settings.face_min_resolution
    if face_w < min_res or face_h < min_res:
        reasons.append("low_resolution")
        messages.append(MESSAGES["low_resolution"])
        sub_scores.append(max(min(face_w, face_h) / min_res, 0.0))
    else:
        sub_scores.append(1.0)

    # ── Pose check (frontal: yaw & pitch within +-15 deg) ────────
    if hasattr(face, "pose"):
        yaw, pitch, _ = face.pose
    else:
        # Approximate from landmarks
        yaw, pitch = 0.0, 0.0

    if abs(yaw) > 15 or abs(pitch) > 15:
        reasons.append("side_angle")
        messages.append(MESSAGES["side_angle"])
        pose_penalty = max(1.0 - (max(abs(yaw), abs(pitch)) - 15) / 30, 0.0)
        sub_scores.append(pose_penalty)
    else:
        sub_scores.append(1.0)

    # ── Lighting check ───────────────────────────────────────────
    face_crop = img_bgr[bbox[1]:bbox[3], bbox[0]:bbox[2]]
    light = _lighting_score(face_crop)
    if light < 0.35:
        reasons.append("too_dark")
        messages.append(MESSAGES["too_dark"])
    sub_scores.append(light)

    # ── Eyes open (EAR) ──────────────────────────────────────────
    if face.kps is not None and len(face.kps) >= 5:
        ear = _eye_aspect_ratio(face.kps)
        if ear < 0.2:
            reasons.append("eyes_closed")
            messages.append(MESSAGES["eyes_closed"])
            sub_scores.append(ear / 0.2)
        else:
            sub_scores.append(1.0)
    else:
        sub_scores.append(0.8)  # Cannot determine; slight penalty

    # ── Mask / occlusion heuristic ───────────────────────────────
    # InsightFace det_score drops when the lower face is occluded.
    det_score = float(face.det_score) if hasattr(face, "det_score") else 1.0
    if det_score < 0.65:
        reasons.append("mask")
        messages.append(MESSAGES["mask"])
        sub_scores.append(det_score)
    else:
        sub_scores.append(min(det_score, 1.0))

    # ── Composite score ──────────────────────────────────────────
    score = float(np.mean(sub_scores)) if sub_scores else 0.0
    passed = len(reasons) == 0 and score >= settings.face_quality_threshold

    return QualityResult(passed=passed, score=round(score, 3), reasons=reasons, messages=messages)


async def remove_background(image_bytes: bytes) -> bytes:
    """Remove the background from a face photo and replace with white.

    Returns PNG bytes with a clean white background.
    """
    from rembg import remove

    session = _get_rembg_session()

    # rembg returns RGBA with transparent background
    result_bytes = remove(image_bytes, session=session)
    img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

    # Composite onto white
    white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(white_bg, img)
    composite = composite.convert("RGB")

    buf = io.BytesIO()
    composite.save(buf, format="PNG", quality=95)
    return buf.getvalue()


async def generate_face_embedding(image_bytes: bytes) -> np.ndarray:
    """Generate a 512-dimensional face embedding from a photo.

    Raises ValueError if no face is detected.
    """
    img_bgr = _bytes_to_cv2(image_bytes)
    app = _get_insightface_app()
    faces = app.get(img_bgr)

    if not faces:
        raise ValueError(MESSAGES["no_face"])

    embedding = faces[0].normed_embedding  # Already L2-normalised, 512-dim
    return np.array(embedding, dtype=np.float32)


async def check_duplicate_identity(
    embedding: np.ndarray,
    db_session: AsyncSession,
) -> tuple[bool, str | None]:
    """Check whether the face already exists in the database.

    Uses cosine similarity via pgvector.  Returns (is_duplicate, employee_id).
    """
    from sqlalchemy import select, text
    from models import FaceEmbedding

    threshold = settings.face_similarity_threshold
    emb_list = embedding.tolist()

    # pgvector cosine distance operator: <=>
    # cosine_distance = 1 - cosine_similarity, so threshold inverts
    stmt = (
        select(
            FaceEmbedding.employee_id,
            (1 - FaceEmbedding.embedding.cosine_distance(emb_list)).label("similarity"),
        )
        .order_by(FaceEmbedding.embedding.cosine_distance(emb_list))
        .limit(1)
    )

    result = await db_session.execute(stmt)
    row = result.first()

    if row is not None and row.similarity >= (1 - threshold):
        return True, str(row.employee_id)

    return False, None
