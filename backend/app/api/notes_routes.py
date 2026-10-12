import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.models.entities import Note, AuditLog
from app.models.schemas import NoteCreate, NoteUpdate, NoteResponse

router = APIRouter(prefix="/api/notes", tags=["Notes"])


@router.get("", response_model=List[NoteResponse])
def list_notes(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    query = db.query(Note)
    if user.role != "admin":
        query = query.filter(Note.owner_id == user.id)
    if search:
        query = query.filter(Note.title.ilike(f"%{search}%") | Note.content.ilike(f"%{search}%"))
    if tag:
        query = query.filter(Note.tags.ilike(f"%{tag}%"))

    notes = query.order_by(Note.updated_at.desc()).offset(offset).limit(limit).all()
    return [
        NoteResponse(
            id=n.id,
            title=n.title,
            content=n.content,
            tags=n.tags,
            owner_id=n.owner_id,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notes
    ]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    req: NoteCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["viewer", "operator", "admin"])),
):
    note = Note(
        id=str(uuid.uuid4()),
        title=req.title,
        content=req.content,
        tags=req.tags or "",
        owner_id=user.id,
    )
    db.add(note)
    audit = AuditLog(
        action="CREATE_NOTE",
        user_id=user.id,
        user_role=user.role,
        resource_type="note",
        resource_id=note.id,
        details_json="{}",
    )
    db.add(audit)
    db.commit()
    db.refresh(note)

    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        tags=note.tags,
        owner_id=note.owner_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if user.role != "admin" and note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to note")

    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        tags=note.tags,
        owner_id=note.owner_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: str,
    req: NoteUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if user.role != "admin" and note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if req.title is not None:
        note.title = req.title
    if req.content is not None:
        note.content = req.content
    if req.tags is not None:
        note.tags = req.tags

    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        tags=note.tags,
        owner_id=note.owner_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if user.role != "admin" and note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db.delete(note)
    db.commit()
    return None


@router.get("/{note_id}/export")
def export_note_markdown(
    note_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    content = f"# {note.title}\n\nTags: {note.tags}\n\n{note.content}\n"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{note.title.replace(" ", "_")}.md"'},
    )


@router.post("/import", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def import_note_markdown(
    req: NoteCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["viewer", "operator", "admin"])),
):
    return create_note(req, db, user)
