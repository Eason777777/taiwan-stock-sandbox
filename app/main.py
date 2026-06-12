from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, saves, accounts, stocks, orders, holdings, watchlist

app = FastAPI(title="錢錢錢市 股票模擬系統")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
