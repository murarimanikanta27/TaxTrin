import pytesseract
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_accessible_client, get_current_user
from app.models.td4 import TD4Input
from app.models.user import User
from app.schemas import TD4Create, TD4OCRResponse, TD4Out
from app.services import ocr as ocr_service
from app.services.entitlements import get_tier_limits

router = APIRouter(prefix="/td4", tags=["td4"])

MAX_OCR_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB -- bumped from the CSV cap to allow multi-page PDF scans
_ALLOWED_OCR_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
    "image/bmp",
    "application/pdf",
}
_ALLOWED_OCR_TYPES_LABEL = "PNG, JPEG, WEBP, TIFF, BMP, or PDF"


@router.post("/ocr", response_model=TD4OCRResponse)
async def ocr_td4_certificate(
    client_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Drag-and-drop TD4 certificate parsing: run OCR/text-extraction on an
    uploaded image or PDF and return raw text plus best-effort extracted
    fields for the frontend's manual-correction UI. PDFs with a native text
    layer (e.g. exported digitally) are read directly; scanned/image-only
    PDF pages fall back to rendering + Tesseract OCR automatically (see
    app.services.ocr). Does not create a TD4Input by itself -- the client
    reviews/edits the suggested fields, then POSTs to /td4 to save them.
    """
    get_accessible_client(client_id, db, current_user)  # 404s if not permitted

    # Some browsers/OSes report a generic content_type (or none) for certain
    # file pickers; fall back to the filename extension so a legitimately
    # supported file isn't rejected on a client-side content-type quirk.
    content_type = file.content_type
    if content_type not in _ALLOWED_OCR_CONTENT_TYPES:
        guessed = _guess_content_type_from_filename(file.filename)
        if guessed in _ALLOWED_OCR_CONTENT_TYPES:
            content_type = guessed

    if content_type not in _ALLOWED_OCR_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Upload a {_ALLOWED_OCR_TYPES_LABEL} file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_OCR_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum upload size is {MAX_OCR_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    try:
        result = ocr_service.run_ocr(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="OCR engine is not available on the server (Tesseract not found). Contact your administrator.",
        ) from exc

    fields = ocr_service.parse_td4_fields(result.raw_text)
    return TD4OCRResponse(
        raw_text=result.raw_text,
        confidence=result.confidence,
        fields=fields,
        page_count=result.page_count,
    )


def _guess_content_type_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
    }.get(ext)


@router.post("", response_model=TD4Out, status_code=201)
def create_td4(payload: TD4Create, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    get_accessible_client(payload.client_id, db, current_user)  # 404s if not permitted

    limits = get_tier_limits(current_user.subscription_tier)
    if limits.max_td4_per_year is not None:
        existing_count = (
            db.query(TD4Input)
            .filter(TD4Input.client_id == payload.client_id, TD4Input.income_year == payload.income_year)
            .count()
        )
        if existing_count >= limits.max_td4_per_year:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Your {current_user.subscription_tier.value} plan allows "
                    f"{limits.max_td4_per_year} TD4 slip(s) per year. Upgrade to Pro for unlimited TD4 processing."
                ),
            )

    td4 = TD4Input(**payload.model_dump())
    db.add(td4)
    db.commit()
    db.refresh(td4)
    return td4


@router.get("", response_model=list[TD4Out])
def list_td4(
    client_id: int,
    income_year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_client(client_id, db, current_user)
    query = db.query(TD4Input).filter(TD4Input.client_id == client_id)
    if income_year is not None:
        query = query.filter(TD4Input.income_year == income_year)
    return query.all()


@router.get("/{td4_id}", response_model=TD4Out)
def get_td4(td4_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    td4 = db.get(TD4Input, td4_id)
    if not td4:
        raise HTTPException(status_code=404, detail="TD4 record not found")
    get_accessible_client(td4.client_id, db, current_user)
    return td4


@router.delete("/{td4_id}", status_code=204)
def delete_td4(td4_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    td4 = db.get(TD4Input, td4_id)
    if not td4:
        raise HTTPException(status_code=404, detail="TD4 record not found")
    get_accessible_client(td4.client_id, db, current_user)
    db.delete(td4)
    db.commit()
