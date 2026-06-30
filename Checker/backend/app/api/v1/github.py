"""
GitHub integration API endpoints.

Handles OAuth, webhooks, repository linking, and automatic scans.
"""

import hashlib
import hmac
import secrets
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Project, Repository, User
from app.schemas import MessageResponse, RepositoryCreate, RepositoryResponse

router = APIRouter(prefix="/github", tags=["GitHub"])
settings = get_settings()


@router.get("/oauth/url")
async def get_github_oauth_url() -> dict[str, str]:
    """
    Get GitHub OAuth authorization URL.

    Frontend redirects user to this URL to initiate OAuth flow.
    """
    state = secrets.token_urlsafe(32)
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_CALLBACK_URL}"
        f"&scope=repo,read:user"
        f"&state={state}"
    )
    return {"url": url, "state": state}


@router.post("/oauth/callback", response_model=MessageResponse)
async def github_oauth_callback(
    code: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Handle GitHub OAuth callback.

    Exchanges authorization code for access token and links to user account.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth not configured",
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        data = response.json()

        if "error" in data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=data["error_description"])

        access_token = data["access_token"]

        # Get GitHub user info
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        github_user = user_response.json()

    current_user.github_id = str(github_user["id"])
    current_user.github_access_token = access_token
    current_user.avatar_url = github_user.get("avatar_url")
    await db.commit()

    return MessageResponse(message="GitHub account linked successfully")


@router.get("/repos")
async def list_github_repos(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """List user's GitHub repositories."""
    if not current_user.github_access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub not connected")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={"Authorization": f"Bearer {current_user.github_access_token}"},
        )
        repos = response.json()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "full_name": r["full_name"],
            "default_branch": r.get("default_branch", "main"),
            "private": r["private"],
            "html_url": r["html_url"],
        }
        for r in repos
    ]


@router.post("/repos/{project_id}", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def link_repository(
    project_id: int,
    repo_data: RepositoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryResponse:
    """Link a GitHub repository to a project."""
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == current_user.id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    repo = Repository(
        project_id=project_id,
        name=repo_data.full_name.split("/")[-1],
        full_name=repo_data.full_name,
        default_branch=repo_data.default_branch,
        auto_scan=repo_data.auto_scan,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        auto_scan=repo.auto_scan,
        last_synced_at=repo.last_synced_at,
    )


@router.post("/webhook")
async def github_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
) -> MessageResponse:
    """
    Handle GitHub webhook events.

    Processes push, pull_request, and other events for automatic validation.
    """
    body = await request.body()

    # Verify webhook signature
    if settings.GITHUB_WEBHOOK_SECRET and x_hub_signature_256:
        expected = "sha256=" + hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    payload = await request.json()

    if not settings.redis_enabled:
        return MessageResponse(
            message=f"Webhook received ({x_github_event}); async processing disabled (Redis not configured)"
        )

    if x_github_event == "push":
        # Queue validation task for push event
        from app.workers.tasks import run_webhook_validation

        repo_full_name = payload.get("repository", {}).get("full_name", "")
        ref = payload.get("ref", "").replace("refs/heads/", "")
        run_webhook_validation.delay(repo_full_name, ref, "push", payload)

    elif x_github_event == "pull_request":
        from app.workers.tasks import run_webhook_validation

        repo_full_name = payload.get("repository", {}).get("full_name", "")
        pr_number = payload.get("pull_request", {}).get("number")
        run_webhook_validation.delay(repo_full_name, str(pr_number), "pull_request", payload)

    return MessageResponse(message=f"Webhook processed: {x_github_event}")
