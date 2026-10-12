import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.models.entities import Conversation, Message, AuditLog
from app.models.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    TreeValidationRequest,
    TreeValidationResponse,
    PromptCompileRequest,
    PromptCompileResponse,
)
from app.services.tree_validator import validate_chat_tree, repair_chat_tree
from app.services.reasoning_filter import extract_reasoning_blocks, compile_prompt_messages
from app.services.llm_client import dispatch_llm_request

router = APIRouter(prefix="/api/chats", tags=["Conversations"])


def to_msg_res(m: Message) -> MessageResponse:
    return MessageResponse(
        id=m.id,
        conversation_id=m.conversation_id,
        parent_id=m.parent_id,
        role=m.role,
        content=m.content,
        reasoning=m.reasoning,
        model=m.model,
        created_at=m.created_at,
        metadata=json.loads(m.metadata_json or "{}"),
    )


def to_conv_res(c: Conversation, include_messages: bool = False) -> ConversationResponse:
    return ConversationResponse(
        id=c.id,
        title=c.title,
        owner_id=c.owner_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
        message_count=len(c.messages),
        messages=[to_msg_res(m) for m in c.messages] if include_messages else None,
        metadata=json.loads(c.metadata_json or "{}"),
    )


@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    query = db.query(Conversation)
    if user.role != "admin":
        query = query.filter(Conversation.owner_id == user.id)
    if search:
        query = query.filter(Conversation.title.ilike(f"%{search}%"))
    conversations = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()
    return [to_conv_res(c) for c in conversations]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: ConversationCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["viewer", "operator", "admin"])),
):
    conv = Conversation(
        id=str(uuid.uuid4()),
        title=req.title,
        owner_id=user.id,
        metadata_json=json.dumps(req.metadata or {}),
    )
    db.add(conv)

    if req.initial_messages:
        for m in req.initial_messages:
            clean, thoughts = extract_reasoning_blocks(m.content)
            reasoning = "\n\n".join(thoughts) if thoughts else m.reasoning
            msg = Message(
                id=m.id or str(uuid.uuid4()),
                conversation_id=conv.id,
                parent_id=m.parent_id,
                role=m.role,
                content=clean or m.content,
                reasoning=reasoning,
                model=m.model,
                metadata_json=json.dumps(m.metadata or {}),
            )
            db.add(msg)

    audit = AuditLog(
        action="CREATE_CONVERSATION",
        user_id=user.id,
        user_role=user.role,
        resource_type="conversation",
        resource_id=conv.id,
        details_json=json.dumps({"title": conv.title}),
    )
    db.add(audit)
    db.commit()
    db.refresh(conv)
    return to_conv_res(conv, include_messages=True)


@router.get("/{chat_id}", response_model=ConversationResponse)
def get_conversation(
    chat_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(Conversation.id == chat_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if user.role != "admin" and conv.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return to_conv_res(conv, include_messages=True)


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(
    chat_id: str,
    req: MessageCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["viewer", "operator", "admin"])),
):
    conv = db.query(Conversation).filter(Conversation.id == chat_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if user.role != "admin" and conv.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    clean, thoughts = extract_reasoning_blocks(req.content)
    parent_id = req.parent_id if req.parent_id is not None else (conv.messages[-1].id if conv.messages else None)

    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        parent_id=parent_id,
        role=req.role,
        content=clean or req.content,
        reasoning="\n\n".join(thoughts) if thoughts else None,
        model=req.model,
        metadata_json=json.dumps(req.metadata or {}),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return to_msg_res(msg)


@router.post("/{chat_id}/generate", response_model=MessageResponse)
async def generate_reply(
    chat_id: str,
    reinject_reasoning: bool = Query(False, description="Reinject reasoning toggle (#23339)"),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    conv = db.query(Conversation).filter(Conversation.id == chat_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    history = [{"role": m.role, "content": m.content, "reasoning": m.reasoning} for m in conv.messages]
    compiled, _, _ = compile_prompt_messages(history, reinject_reasoning=reinject_reasoning)
    llm_resp = await dispatch_llm_request(compiled)

    clean, thoughts = extract_reasoning_blocks(llm_resp.content)
    final_reasoning = llm_resp.reasoning or ("\n\n".join(thoughts) if thoughts else None)
    parent_id = conv.messages[-1].id if conv.messages else None

    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        parent_id=parent_id,
        role="assistant",
        content=clean or llm_resp.content,
        reasoning=final_reasoning,
        model=llm_resp.model,
        metadata_json=json.dumps({"provider": llm_resp.provider, "usage": llm_resp.usage}),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return to_msg_res(assistant_msg)


@router.post("/validate-tree", response_model=TreeValidationResponse)
def validate_tree_endpoint(req: TreeValidationRequest, user: AuthenticatedUser = Depends(get_current_user)):
    is_valid, errors, warnings, orphan_count, cycle_detected = validate_chat_tree(req.messages)
    repaired = repair_chat_tree(req.messages) if (req.auto_repair or not is_valid) else None
    return TreeValidationResponse(
        is_valid=is_valid,
        orphan_count=orphan_count,
        cycle_detected=cycle_detected,
        errors=errors,
        warnings=warnings,
        repaired_messages=repaired,
    )


@router.post("/compile-prompt", response_model=PromptCompileResponse)
def compile_prompt_endpoint(
    req: PromptCompileRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        messages = [{"role": m.role, "content": m.content, "reasoning": m.reasoning} for m in conv.messages]
    elif req.messages:
        messages = req.messages
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide conversation_id or messages")

    compiled, pruned_count, est_tokens = compile_prompt_messages(
        messages, reinject_reasoning=req.reinject_reasoning, max_context_messages=req.max_context_messages
    )
    return PromptCompileResponse(
        compiled_messages=compiled,
        reinject_reasoning=req.reinject_reasoning,
        reasoning_blocks_pruned=pruned_count,
        estimated_tokens=est_tokens,
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    chat_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    conv = db.query(Conversation).filter(Conversation.id == chat_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if user.role != "admin" and conv.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db.delete(conv)
    audit = AuditLog(
        action="DELETE_CONVERSATION",
        user_id=user.id,
        user_role=user.role,
        resource_type="conversation",
        resource_id=chat_id,
        details_json="{}",
    )
    db.add(audit)
    db.commit()
    return None
