from __future__ import annotations

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder

from app.application.services import (
    execute_market_workflow,
    save_holdings,
    read_holdings,
    read_market_item_history,
    read_market_snapshot,
    read_market_types,
)


def create_app() -> FastAPI:
    app = FastAPI(title="POE Helper API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "POE Helper API",
            "status": "ok",
            "docs": "/docs",
        }

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"ok": True, "service": "poe-helper", "layer": "api"}

    @app.get("/api/market/types")
    def market_types() -> dict[str, object]:
        return {"ok": True, "market_types": read_market_types()}

    @app.get("/api/market/latest")
    def latest_market(
        league: str = Query("Runes of Aldur"),
        market_type: str = Query("Currency"),
        limit: int = Query(10, ge=1, le=100),
    ) -> dict[str, object]:
        snapshot = read_market_snapshot(league=league, market_type=market_type, limit=limit)
        if not snapshot.ok:
            raise HTTPException(status_code=404, detail=snapshot.error or "No market snapshot found.")
        return jsonable_encoder(snapshot)

    @app.get("/api/market/history/{item_id}")
    def item_history(
        item_id: str,
        league: str = Query("Runes of Aldur"),
        market_type: str = Query("Currency"),
    ) -> dict[str, object]:
        history = read_market_item_history(league=league, market_type=market_type, item_id=item_id)
        if not history.ok:
            raise HTTPException(status_code=404, detail=history.error or "No item history found.")
        return jsonable_encoder(history)

    @app.post("/api/market/refresh")
    def refresh_market(
        league: str = Query("Runes of Aldur"),
        market_type: str = Query("all"),
        market_out_dir: str = Query("data/market"),
        market_limit: int = Query(10, ge=1, le=100),
        recommend: bool = Query(False),
        source_currency: str = Query("exalt"),
    ) -> dict[str, object]:
        response = execute_market_workflow(
            league=league,
            market_type=market_type,
            market_out_dir=market_out_dir,
            market_limit=market_limit,
            vendor_file=None,
            min_margin=0.0,
            convert=False,
            from_currency=None,
            to_currency=None,
            amount=1.0,
            flip_route_file=None,
            flip_route_name=None,
            recommend=recommend,
            source_currency=source_currency,
        )
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.error or "Market refresh failed.")
        return jsonable_encoder(response)

    @app.get("/api/holdings")
    def get_holdings(
        league: str = Query("Runes of Aldur"),
        market_type: str = Query("Currency"),
    ) -> dict[str, object]:
        response = read_holdings(league=league, market_type=market_type)
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.error or "Failed to load holdings.")
        return jsonable_encoder(response)

    @app.post("/api/holdings")
    def post_holdings(
        payload: dict[str, object] = Body(...),
    ) -> dict[str, object]:
        league = str(payload.get("league") or "Runes of Aldur").strip() or "Runes of Aldur"
        market_type = str(payload.get("market_type") or "Currency").strip() or "Currency"
        items = payload.get("items")
        if not isinstance(items, list):
            raise HTTPException(status_code=422, detail="Payload must include an items list.")

        response = save_holdings(league=league, market_type=market_type, items=items)
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.error or "Failed to save holdings.")
        return jsonable_encoder(response)

    return app


app = create_app()