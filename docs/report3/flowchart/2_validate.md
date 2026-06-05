flowchart TD
    subgraph REG[註冊 POST /auth/register]
    A1[送出 account + password] --> A2{account 已存在?}
    A2 -- 是 --> A3[409 帳號已存在]
    A2 -- 否 --> A4[bcrypt 雜湊密碼]
    A4 --> A5[INSERT users<br/>session_id = NULL]
    A5 --> A6[201 註冊成功]
    end

    subgraph LOGIN[登入 POST /auth/login]
    B1[送出 account + password] --> B2{帳號存在?}
    B2 -- 否 --> B3[401 帳號或密碼錯誤]
    B2 -- 是 --> B4{bcrypt 驗證密碼?}
    B4 -- 否 --> B3
    B4 -- 是 --> B5[產生新 session_id<br/>secrets.token_hex#40;18#41;]
    B5 --> B6[UPDATE users.session_id<br/>舊 session 立即失效]
    B6 --> B7[回傳 session_id]
    end

    subgraph REQ[每次請求:受保護路由]
    C1[請求帶 X-Session-Id 標頭] --> C2{標頭存在?}
    C2 -- 否 --> C3[422 缺少標頭]
    C2 -- 是 --> C4{session_id 對應到 user?}
    C4 -- 否 --> C5[401 Not authenticated]
    C4 -- 是 --> C6[注入 current_user<br/>進入路由邏輯]
    end

    subgraph OUT[登出 POST /auth/logout]
    D1[已驗證使用者] --> D2[UPDATE session_id = NULL]
    end
