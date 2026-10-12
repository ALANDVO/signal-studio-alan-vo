import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.models.entities import EvaluationRun, AuditLog
from app.models.schemas import EvaluationRunRequest, EvaluationRunResponse
from app.services.eval_runner import run_benchmark_suite

router = APIRouter(prefix="/api/eval", tags=["Evaluation Suite"])


@router.post("/run", response_model=EvaluationRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_benchmark(
    req: EvaluationRunRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_role(["operator", "admin"])),
):
    results = run_benchmark_suite()

    run = EvaluationRun(
        id=str(uuid.uuid4()),
        title=req.title or f"Run {results['benchmark_name']}",
        benchmark_name=results["benchmark_name"],
        sample_count=results["sample_count"],
        structural_integrity_score=results["structural_integrity_score"],
        reasoning_isolation_score=results["reasoning_isolation_score"],
        retrieval_f1_score=results["retrieval_f1_score"],
        accuracy_score=results["accuracy_score"],
        metrics_json=json.dumps(results["metrics"]),
    )
    db.add(run)

    audit = AuditLog(
        action="EVAL_EXECUTE",
        user_id=user.id,
        user_role=user.role,
        resource_type="evaluation_run",
        resource_id=run.id,
        details_json=json.dumps({"accuracy": run.accuracy_score}),
    )
    db.add(audit)
    db.commit()
    db.refresh(run)

    return EvaluationRunResponse(
        id=run.id,
        title=run.title,
        benchmark_name=run.benchmark_name,
        sample_count=run.sample_count,
        structural_integrity_score=run.structural_integrity_score,
        reasoning_isolation_score=run.reasoning_isolation_score,
        retrieval_f1_score=run.retrieval_f1_score,
        accuracy_score=run.accuracy_score,
        metrics=json.loads(run.metrics_json or "{}"),
        created_at=run.created_at,
    )


@router.get("/runs", response_model=List[EvaluationRunResponse])
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).offset(offset).limit(limit).all()
    return [
        EvaluationRunResponse(
            id=r.id,
            title=r.title,
            benchmark_name=r.benchmark_name,
            sample_count=r.sample_count,
            structural_integrity_score=r.structural_integrity_score,
            reasoning_isolation_score=r.reasoning_isolation_score,
            retrieval_f1_score=r.retrieval_f1_score,
            accuracy_score=r.accuracy_score,
            metrics=json.loads(r.metrics_json or "{}"),
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=EvaluationRunResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    r = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")

    return EvaluationRunResponse(
        id=r.id,
        title=r.title,
        benchmark_name=r.benchmark_name,
        sample_count=r.sample_count,
        structural_integrity_score=r.structural_integrity_score,
        reasoning_isolation_score=r.reasoning_isolation_score,
        retrieval_f1_score=r.retrieval_f1_score,
        accuracy_score=r.accuracy_score,
        metrics=json.loads(r.metrics_json or "{}"),
        created_at=r.created_at,
    )
