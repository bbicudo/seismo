"""Sugestões de correção ("Encontrou um erro?").

As rotas ficam sob /v1/admin, que o proxy não expõe: só o servidor do site (formulário) e o /admin chegam aqui.
Não guardamos IP: o site manda um hash diário do endereço só para limitar envios por hora no Redis.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from . import main as m

router = APIRouter()

FEATURES = {"hunts", "yasir", "site"}


class FeedbackIn(BaseModel):
    feature: str
    message: str = Field(min_length=10, max_length=2000)
    page: str | None = Field(default=None, max_length=300)
    locale: str | None = Field(default=None, max_length=5)
    client: str = Field(min_length=8, max_length=128)  # hash diário do endereço, nunca o IP


@router.post("/v1/admin/feedback")
async def submit(body: FeedbackIn, response: Response):
    response.headers["Cache-Control"] = "no-store"
    await m.require("feedback_form")
    if body.feature not in FEATURES:
        raise HTTPException(422, "parte do site desconhecida")
    limit = int((await m.params()).get("feedback_per_hour", 5))
    key = f"seismo:feedback:{body.client}"
    n = await m.app.state.redis.incr(key)
    if n == 1:
        await m.app.state.redis.expire(key, 3600)
    if n > limit:
        raise HTTPException(429, "muitos envios; tente de novo em uma hora")
    page = (body.page or "").strip() or None
    if page and not page.startswith("/"):
        page = None  # só caminhos do próprio site
    await m.query(
        "INSERT INTO feedback (feature, page, message, locale) VALUES (%s, %s, %s, %s)",
        body.feature, page, body.message.strip(), body.locale if body.locale in ("pt", "en") else None,
    )
    return {"ok": True}


@router.get("/v1/admin/feedback")
async def list_feedback(response: Response):
    response.headers["Cache-Control"] = "no-store"
    rows = await m.query(
        "SELECT id, created_at, feature, page, message, locale, resolved FROM feedback "
        "ORDER BY resolved, created_at DESC LIMIT 200"
    )
    pending = await m.query("SELECT count(*)::int AS n FROM feedback WHERE NOT resolved")
    return {"items": rows, "pending": pending[0]["n"]}


class FeedbackAction(BaseModel):
    action: str  # resolve | reopen | delete


@router.post("/v1/admin/feedback/{fid}")
async def act(fid: int, body: FeedbackAction, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if body.action == "delete":
        await m.query("DELETE FROM feedback WHERE id = %s", fid)
    elif body.action in ("resolve", "reopen"):
        await m.query("UPDATE feedback SET resolved = %s WHERE id = %s", body.action == "resolve", fid)
    else:
        raise HTTPException(422, "ação desconhecida")
    return {"ok": True}
