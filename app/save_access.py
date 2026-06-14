from fastapi import HTTPException
from .database import SqlApiClient


async def fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient, columns: str = "*") -> dict:
    """共用的存檔存取檢查：確認存檔存在且屬於目前使用者，回傳指定欄位。

    columns 必須包含 user_id（用於擁有權檢查）。
    """
    result = await db.query(
        f"SELECT {columns} FROM save_files WHERE save_id = ?", [int(save_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result["rows"][0]
    if int(save["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save
