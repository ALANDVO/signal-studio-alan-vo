import hashlib
import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.models.entities import KnowledgeDocument, KnowledgeChunk, AuditLog
from app.models.schemas import (
    DocumentIngestRequest,
    KnowledgeDocumentResponse,
    KnowledgeChunkResponse,
    ChunkSearchRequest,
    ChunkSearchResponse,
)
from app.services.content_extractor import extract_content, search_knowledge_chunks

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


def to_doc_res(d: KnowledgeDocument, include_chunks: bool = False) -> KnowledgeDocumentResponse:
    chunks = [
        KnowledgeChunkResponse(
            id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            text=c.text,
            token_count=c.token_count,
            heading=c.heading,
        )
        for c in d.chunks
    ] if include_chunks else None
    return KnowledgeDocumentResponse(
        id=d.id,
        name=d.name,
        strategy=d.strategy,
        content_hash=d.content_hash,
        chunk_count=d.chunk_count,
        owner_id=d.owner_id,
        created_at=d.created_at,
        chunks=chunks,
    )


@router.get("/documents", response_model=List[KnowledgeDocumentResponse])
def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    query = db.query(KnowledgeDocument)
    if user.role != "admin":
        query = query.filter(KnowledgeDocument.owner_id == user.id)
    docs = query.order_by(KnowledgeDocument.created_at.desc()).offset(offset).limit(limit).all()
    return [to_doc_res(d) for d in docs]


@router.post("/documents", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
def ingest_document(
    req: DocumentIngestRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    strategy = req.strategy.lower()
    if strategy not in ("fast_text", "structured_markdown", "semantic_chunks"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported extraction strategy '{req.strategy}'",
        )

    content_hash = hashlib.sha256(req.content.encode("utf-8")).hexdigest()
    doc_id = str(uuid.uuid4())
    chunks_data = extract_content(req.content, strategy=strategy)

    doc = KnowledgeDocument(
        id=doc_id,
        name=req.name,
        strategy=strategy,
        content_hash=content_hash,
        chunk_count=len(chunks_data),
        owner_id=user.id,
    )
    db.add(doc)

    for ch in chunks_data:
        chunk_obj = KnowledgeChunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=ch["chunk_index"],
            text=ch["text"],
            token_count=ch["token_count"],
            heading=ch.get("heading"),
            metadata_json=json.dumps(ch.get("metadata", {})),
        )
        db.add(chunk_obj)

    audit = AuditLog(
        action="INGEST_DOCUMENT",
        user_id=user.id,
        user_role=user.role,
        resource_type="knowledge_document",
        resource_id=doc_id,
        details_json=json.dumps({"name": req.name, "strategy": strategy, "chunks": len(chunks_data)}),
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)
    return to_doc_res(doc)


@router.get("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if user.role != "admin" and doc.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return to_doc_res(doc, include_chunks=True)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if user.role != "admin" and doc.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    db.delete(doc)
    db.commit()
    return None


@router.post("/search", response_model=ChunkSearchResponse)
def search_chunks(
    req: ChunkSearchRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    query = db.query(KnowledgeChunk).join(KnowledgeDocument)
    if user.role != "admin":
        query = query.filter(KnowledgeDocument.owner_id == user.id)
    if req.strategy_filter:
        query = query.filter(KnowledgeDocument.strategy == req.strategy_filter.lower())

    chunks = query.all()
    chunk_dicts = [
        {"id": c.id, "document_id": c.document_id, "chunk_index": c.chunk_index, "text": c.text, "token_count": c.token_count, "heading": c.heading}
        for c in chunks
    ]
    matches = search_knowledge_chunks(chunk_dicts, req.query, limit=req.limit)
    return ChunkSearchResponse(
        query=req.query,
        matches=[
            KnowledgeChunkResponse(
                id=m["id"],
                document_id=m["document_id"],
                chunk_index=m["chunk_index"],
                text=m["text"],
                token_count=m["token_count"],
                heading=m.get("heading"),
                score=m.get("score"),
            )
            for m in matches
        ],
    )
