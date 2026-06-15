# 共用常數，供 auth 與 dependencies 一同 import，避免兩處各寫一份導致不一致，
# 也避免 auth.py 與 dependencies.py 互相 import 造成循環依賴。

# session 有效期限：每次通過驗證的請求都會把過期時間滑動延長至 NOW() + 此小時數，
# 因此這是「閒置上限」（idle timeout），而非從登入起算的總時長上限。
SESSION_TTL_HOURS = 0.009

# MySQL 的 `INTERVAL <小數> HOUR` 會把小數部分截斷成整數（例如 0.009、甚至 0.25
# 都會變成 INTERVAL 0 HOUR，使 session 一發出即過期）。因此 SQL 一律改用秒為單位，
# 由小時換算成整數秒後嵌入 `INTERVAL <秒> SECOND`，小數小時也能精確表示。
SESSION_TTL_SECONDS = int(round(SESSION_TTL_HOURS * 3600))
