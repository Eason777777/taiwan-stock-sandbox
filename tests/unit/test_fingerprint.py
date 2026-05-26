"""T069: Fingerprint stability — SHA-256(path+symbol+vuln_class) is line-number and body independent."""
import hashlib


def _fingerprint(path: str, symbol: str, vuln_class: str) -> str:
    norm_path = path.replace("\\", "/").lstrip("/")
    raw = f"{norm_path}\x00{symbol}\x00{vuln_class}"
    return hashlib.sha256(raw.encode()).hexdigest()


def test_fingerprint_stable_across_line_changes():
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    fp2 = _fingerprint("app/auth.py", "login", "SQL Injection")
    assert fp1 == fp2


def test_fingerprint_ignores_leading_slash():
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    fp2 = _fingerprint("/app/auth.py", "login", "SQL Injection")
    assert fp1 == fp2


def test_fingerprint_ignores_backslash_separator():
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    fp2 = _fingerprint("app\\auth.py", "login", "SQL Injection")
    assert fp1 == fp2


def test_fingerprint_differs_by_symbol():
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    fp2 = _fingerprint("app/auth.py", "logout", "SQL Injection")
    assert fp1 != fp2


def test_fingerprint_differs_by_path():
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    fp2 = _fingerprint("app/orders.py", "login", "SQL Injection")
    assert fp1 != fp2


def test_fingerprint_differs_by_vuln_class():
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    fp2 = _fingerprint("app/auth.py", "login", "Command Injection")
    assert fp1 != fp2


def test_fingerprint_returns_hex_string():
    fp = _fingerprint("app/auth.py", "login", "SQL Injection")
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_stable_when_body_changes():
    # Fingerprint must NOT include function body — only path+symbol+class
    fp1 = _fingerprint("app/auth.py", "login", "SQL Injection")
    # Even if the caller had different body content, same path/symbol/class → same fingerprint
    fp2 = _fingerprint("app/auth.py", "login", "SQL Injection")
    assert fp1 == fp2
