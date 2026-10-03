"""
InternShield — Analysis Router

Handles file upload, text extraction, ML pipeline, and result storage.
"""

import os
import re
import time
import uuid
from typing import Optional
from collections import OrderedDict

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from supabase import create_client, Client

from models.schemas import (
    AnalysisResponse,
    HistoryResponse,
    ScanRecord,
    InputType,
)
from services.text_extractor import (
    extract_from_pdf,
    extract_from_image,
    extract_from_docx,
    extract_from_txt,
    extract_from_text,
    compute_file_hash,
)
from services.rule_engine import run_all_rules
from services.nlp_classifier import classify_text
from services.ner_extractor import extract_and_verify
from services.company_evidence import evaluate_company_evidence
from services.scorer import compute_final_score, get_next_steps

router = APIRouter()

# Supabase client (optional — app works without it)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None


# In-memory LRU result cache (max 200 entries)
class LRUCache(OrderedDict):
    def __init__(self, maxsize=200):
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value


_result_cache: LRUCache = LRUCache(200)
_history_cache: dict[str, list[dict]] = {}


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: str = Form(...),
    company_name_input: Optional[str] = Form(None),
    company_website: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
):
    """
    Analyze an offer letter for authenticity.
    Accepts PDF, image, DOCX, TXT, or plain text.
    Optional: company name, website, and contact email for enriched analysis.
    """
    start_time = time.time()

    # --- Step 1: Extract text ---
    extracted_text = ""
    input_type = InputType.TEXT
    extraction_method = "direct"
    file_hash = ""

    if file and file.filename:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File size must be 10 MB or smaller.")
        file_hash = compute_file_hash(file_bytes)
        filename_lower = file.filename.lower()

        if filename_lower.endswith(".pdf"):
            input_type = InputType.PDF
            extracted_text, extraction_method = extract_from_pdf(file_bytes)
        elif filename_lower.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")):
            input_type = InputType.IMAGE
            extracted_text, extraction_method = extract_from_image(file_bytes)
        elif filename_lower.endswith((".docx",)):
            input_type = InputType.TEXT
            extracted_text, extraction_method = extract_from_docx(file_bytes)
        elif filename_lower.endswith((".txt", ".rtf")):
            input_type = InputType.TEXT
            extracted_text, extraction_method = extract_from_txt(file_bytes)
        elif filename_lower.endswith((".doc",)):
            raise HTTPException(
                status_code=400,
                detail="Old .doc format is not supported. Please save the file as .docx or .pdf and try again.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Upload a PDF, DOCX, JPG, PNG, WEBP, BMP, TIFF, TXT, or RTF file.",
            )
    elif text and text.strip():
        input_type = InputType.TEXT
        extracted_text, extraction_method = extract_from_text(text)
        file_hash = compute_file_hash(text.encode("utf-8"))
    else:
        raise HTTPException(
            status_code=400,
            detail="Please provide either a file upload or text input.",
        )

    if extraction_method in {"tesseract_unavailable", "tesseract_not_installed"}:
        raise HTTPException(
            status_code=503,
            detail="Image OCR is not installed on this device. Install Tesseract OCR, then restart the backend and upload the image again.",
        )

    if not extracted_text or len(extracted_text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Could not extract sufficient text from the input. Please try a clearer image or paste the text directly.",
        )

    # --- Step 1b: Cross-check supplied identity details ---
    # This deliberately does not use a popularity/famous-company list.
    enrichment_flags = evaluate_company_evidence(
        company_name_input, company_website, contact_email
    )

    # --- Step 2: Run ML pipeline ---

    # Rule-based engine
    rule_suspicion, rule_flags = run_all_rules(extracted_text)

    # NLP classifier
    nlp_confidence, nlp_flags = classify_text(extracted_text)

    # NER extraction & verification
    ner_score, ner_flags, entities = extract_and_verify(
        extracted_text,
        company_name_hint=company_name_input,
        contact_email_hint=contact_email,
    )

    # Concrete supplied-detail warnings must affect the verdict, not just the UI.
    if enrichment_flags:
        rule_suspicion = min(
            1.0,
            rule_suspicion + max(flag["score"] for flag in enrichment_flags) * 0.35,
        )

    # Combine all flags (enrichment + rule + NLP + NER)
    all_flags = enrichment_flags + rule_flags + nlp_flags + ner_flags

    # --- Step 3: Compute final score ---
    final_score, verdict, dimension_scores = compute_final_score(
        nlp_confidence=nlp_confidence,
        rule_suspicion=rule_suspicion,
        ner_verification=ner_score,
        flag_count=len(all_flags),
    )

    # Sort flags by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_flags.sort(key=lambda f: severity_order.get(f.get("severity", "low"), 4))

    # Get next steps
    company_name = entities.get("company_name")
    next_steps = get_next_steps(verdict, company_name)

    processing_time_ms = int((time.time() - start_time) * 1000)

    # --- Step 4: Build result ---
    scan_id = str(uuid.uuid4())

    result_data = {
        "id": scan_id,
        "input_type": input_type.value,
        "extracted_text": extracted_text[:10000],
        "confidence_score": final_score,
        "verdict": verdict.value,
        "dimension_scores": dimension_scores.model_dump(),
        "triggered_flags": all_flags,
        "next_steps": next_steps,
        "company_name": company_name,
        "session_id": session_id,
        "file_hash": file_hash,
        "extraction_method": extraction_method,
        "processing_time_ms": processing_time_ms,
        "model_version": "v1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Save to in-memory cache (always works)
    _result_cache[scan_id] = result_data

    # Track in session history
    if session_id not in _history_cache:
        _history_cache[session_id] = []
    _history_cache[session_id].insert(0, {
        "id": scan_id,
        "created_at": result_data["created_at"],
        "confidence_score": final_score,
        "verdict": verdict.value,
        "company_name": company_name,
        "input_type": input_type.value,
    })

    # Save to Supabase (optional)
    if supabase:
        try:
            supabase.table("scans").insert({
                k: v for k, v in result_data.items()
                if k not in ("created_at",)
            }).execute()
        except Exception as e:
            print(f"Supabase insert error: {e}")

    # --- Step 5: Return response ---
    return AnalysisResponse(
        id=scan_id,
        confidence_score=final_score,
        verdict=verdict,
        dimension_scores=dimension_scores,
        triggered_flags=all_flags,
        next_steps=next_steps,
        company_name=company_name,
        input_type=input_type,
        extraction_method=extraction_method,
        processing_time_ms=processing_time_ms,
    )


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """Get scan history for a specific session."""
    if supabase:
        try:
            response = (
                supabase.table("scans")
                .select("id, created_at, confidence_score, verdict, company_name, input_type")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            scans = [
                ScanRecord(
                    id=row["id"],
                    created_at=row["created_at"],
                    confidence_score=row["confidence_score"],
                    verdict=row["verdict"],
                    company_name=row.get("company_name"),
                    input_type=row["input_type"],
                )
                for row in response.data
            ]
            return HistoryResponse(scans=scans, total=len(scans))
        except Exception as e:
            print(f"Supabase query error: {e}")

    # Fallback: in-memory history
    cached_history = _history_cache.get(session_id, [])
    scans = [
        ScanRecord(
            id=row["id"],
            created_at=row["created_at"],
            confidence_score=row["confidence_score"],
            verdict=row["verdict"],
            company_name=row.get("company_name"),
            input_type=row["input_type"],
        )
        for row in cached_history[:50]
    ]
    return HistoryResponse(scans=scans, total=len(scans))


@router.get("/result/{scan_id}")
async def get_result(scan_id: str):
    """Get full result for a specific scan."""
    if supabase:
        try:
            response = (
                supabase.table("scans")
                .select("*")
                .eq("id", scan_id)
                .single()
                .execute()
            )
            if response.data:
                return response.data
        except Exception as e:
            print(f"Supabase query error: {e}")

    if scan_id in _result_cache:
        return _result_cache[scan_id]

    raise HTTPException(status_code=404, detail="Scan not found")
