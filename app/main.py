import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import auth, saves, accounts, stocks, orders, holdings, watchlist

app = FastAPI(title="錢錢錢市 股票模擬系統")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sanitize_non_finite(value):
    """將 NaN/Infinity/-Infinity 取代為字串，避免 JSONResponse(allow_nan=False) 在
    序列化驗證錯誤內容（含請求中原始的 NaN/Infinity 數值）時 raise ValueError -> 500。"""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _sanitize_non_finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_non_finite(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = jsonable_encoder(exc.errors())
    return JSONResponse(status_code=422, content={"detail": _sanitize_non_finite(errors)})

app.include_router(auth.router)
app.include_router(saves.router)
app.include_router(accounts.router)
app.include_router(stocks.router)
app.include_router(orders.router)
app.include_router(holdings.router)
app.include_router(watchlist.router)


@app.get("/")
async def root():
    return {"message": "錢錢錢市 API is running"}
