from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
import project_store
import report_store
import user_store
import subscription_store

# The API is a separate process; load its own provider configuration.
user_store.load_local_environment()

app = FastAPI()
bearer = HTTPBearer(auto_error=False)


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=30000)
    project_id: int = Field(gt=0)

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Query must contain text.")
        return value


class AnalyzeResponse(BaseModel):
    id: str
    project_id: int
    result: str
    sources: list[dict]
    status: str
    version: str


def authenticated_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    user = user_store.resolve_session(credentials.credentials) if credentials else None
    if user is None:
        raise HTTPException(401, "A valid, unexpired session is required.", headers={"WWW-Authenticate": "Bearer"})
    return user


def authorize_project(user, project_id):
    try:
        project_store.require_project_access(user['id'], project_id)
    except (PermissionError, ValueError):
        raise HTTPException(404, "Project not found.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, user=Depends(authenticated_user)):
    authorize_project(user, request.project_id)
    try:
        subscription_store.increment_ai_request(user['id'])
    except PermissionError as exc:
        raise HTTPException(429, str(exc))
    from core.engine import run_engine
    try:
        payload = run_engine(str(user['id']), request.query.strip(), project_id=request.project_id, return_details=True)
        return report_store.save_report(user['id'], request.project_id, {**payload, "query": request.query, "mode": "Copilot"})
    except PermissionError:
        raise HTTPException(404, "Project not found.")
    except Exception:
        raise HTTPException(502, "Analysis failed. No report was saved; please retry.")


@app.get("/projects/{project_id}/reports")
def reports(project_id: int, user=Depends(authenticated_user)):
    authorize_project(user, project_id)
    return report_store.list_reports(user['id'], project_id)


@app.get("/projects/{project_id}/reports/{report_id}")
def report(project_id: int, report_id: str, user=Depends(authenticated_user)):
    authorize_project(user, project_id)
    result = report_store.get_report(user['id'], project_id, report_id)
    if result is None:
        raise HTTPException(404, "Report not found.")
    return result
