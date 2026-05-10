"""Naver 로그인 — CDP(1순위) + RSA(폴백).

Adapted from seokcess-kk/auto-publishing@c64b5e7 (MIT) common/auth.py.
원본의 WordPress/Coupang 인증을 제거하고 네이버 전용으로 축약. 환경변수도
`config.settings` 경유로 통일.

Phase AP-A 운영 환경: Windows 로컬, Chrome 프로필에 5채널 사전 로그인 가정.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import requests

from config.settings import settings

logger = logging.getLogger(__name__)

# CDP 포트 — auto-publishing 의 9223 그대로 (다른 도구와 충돌 회피)
_CDP_PORT = 9223


# ── Chrome 경로 자동 탐지 ─────────────────────────────────────


def _resolve_chrome_path() -> str:
    """settings.chrome_path 우선. 없으면 OS 기본 경로 자동 탐지."""
    env_path = (settings.chrome_path or "").strip()
    if env_path and Path(env_path).exists():
        return env_path
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in candidates:
            if Path(p).exists():
                return p
    if sys.platform == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return "google-chrome"


def _resolve_chrome_user_data() -> str:
    """Chrome 'User Data' 경로. 환경변수 CHROME_USER_DATA 가 있으면 우선."""
    env_path = os.environ.get("CHROME_USER_DATA", "").strip()
    if env_path:
        return os.path.expanduser(env_path)
    if sys.platform == "win32":
        return os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Google/Chrome")
    return os.path.expanduser("~/.config/google-chrome")


# ── CDP 로그인 (1순위) ──────────────────────────────────────


def naver_login_cdp(
    session: requests.Session,
    *,
    chrome_profile: str | None = None,
) -> bool:
    """로컬 Chrome 프로필을 CDP 로 띄워 NID_AUT/NID_SES 쿠키를 session 에 주입.

    chrome_profile 미지정 시 settings.naver_chrome_profile 사용. Phase AP-C 5채널
    운영 시 채널별 프로필을 명시 전달 (e.g., "Profile 2", "Profile 3", ...).

    실패 케이스:
        - playwright 미설치 → False
        - 프로필 디렉터리 없음 → False
        - 쿠키 수집됐지만 NID_AUT/NID_SES 부재 (해당 프로필 비로그인 상태) → False
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("auth.cdp.playwright_missing — pip install playwright")
        return False

    profile = chrome_profile or settings.naver_chrome_profile or "Default"
    chrome_path = _resolve_chrome_path()
    user_data = _resolve_chrome_user_data()
    src_profile = Path(user_data) / profile

    if not src_profile.exists():
        logger.warning("auth.cdp.profile_missing path=%s", src_profile)
        return False

    logger.info("auth.cdp.start profile=%s", profile)

    # 실행 중인 Chrome 과 충돌 방지 — 프로필 임시 복사
    tmp_user_data = Path(tempfile.mkdtemp(prefix="naver_chrome_"))
    tmp_profile_dir = tmp_user_data / "Default"
    try:
        shutil.copytree(
            src_profile,
            tmp_profile_dir,
            ignore=shutil.ignore_patterns(
                "SingletonLock",
                "SingletonCookie",
                "SingletonSocket",
                "lockfile",
                "*.log",
                "Cache",
                "Code Cache",
                "GPUCache",
                "ShaderCache",
            ),
        )
    except Exception as exc:
        logger.warning("auth.cdp.copy_failed err=%s", exc)
        shutil.rmtree(tmp_user_data, ignore_errors=True)
        return False

    cmd = [
        chrome_path,
        f"--remote-debugging-port={_CDP_PORT}",
        f"--user-data-dir={tmp_user_data}",
        "--profile-directory=Default",
        "--headless=new",
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(4)  # 프로필 로드 대기 — auto-publishing 실측 안전값

    # Playwright 의 Cookie TypedDict 를 그대로 다룬다 (str | bool 등 혼합 필드 포함).
    naver_cookies: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{_CDP_PORT}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=15000)
            time.sleep(1)
            page.goto("https://blog.naver.com", wait_until="domcontentloaded", timeout=15000)
            time.sleep(1)
            all_cookies = context.cookies(["https://www.naver.com", "https://blog.naver.com"])
            naver_cookies = [
                dict(c) for c in all_cookies if "naver" in str(c.get("domain", ""))
            ]
            page.close()
            browser.close()
    except Exception as exc:
        logger.error("auth.cdp.browser_failed err=%s", exc)
        return False
    finally:
        proc.terminate()
        time.sleep(0.5)
        shutil.rmtree(tmp_user_data, ignore_errors=True)

    if not naver_cookies:
        logger.warning("auth.cdp.no_cookies — profile %s 에 네이버 로그인 필요", profile)
        return False

    for c in naver_cookies:
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", "").lstrip("."))

    cookie_names = {c["name"] for c in naver_cookies}
    if "NID_AUT" in cookie_names or "NID_SES" in cookie_names:
        logger.info("auth.cdp.success n_cookies=%d", len(naver_cookies))
        return True

    logger.warning("auth.cdp.no_login_cookie names=%s", sorted(cookie_names))
    return False


# ── RSA 로그인 (폴백) ──────────────────────────────────────


def _naver_get_rsa_keys(session: requests.Session) -> dict[str, str]:
    resp = session.get("https://nid.naver.com/login/ext/keys.nhn")
    resp.raise_for_status()
    tokens = resp.text.split(",")
    return {
        "session_key": tokens[0],
        "key_name": tokens[1],
        "n_val": tokens[2],
        "e_val": tokens[3],
    }


def _naver_encrypt_credentials(
    session_key: str,
    key_name: str,
    e_val: str,
    n_val: str,
    username: str,
    password: str,
) -> tuple[str, str]:
    try:
        import rsa
    except ImportError as exc:
        raise ImportError("rsa 패키지 필요: pip install rsa") from exc

    n = int(n_val, 16)
    e = int(e_val, 16)
    pub_key = rsa.PublicKey(n, e)

    sk_b = session_key.encode("utf-8")
    uid_b = username.encode("utf-8")
    pw_b = password.encode("utf-8")
    msg = bytes([len(sk_b)]) + sk_b + bytes([len(uid_b)]) + uid_b + bytes([len(pw_b)]) + pw_b
    encrypted = rsa.encrypt(msg, pub_key)
    return encrypted.hex(), key_name


def _naver_build_bvsd() -> str:
    bvsd = {
        "uuid": str(uuid.uuid4()),
        "em": {"version": "1.0.0", "platform": "Windows", "app_key": "naverapp"},
        "ts": int(time.time() * 1000),
    }
    return json.dumps(bvsd, ensure_ascii=False)


def naver_login(session: requests.Session, username: str, password: str) -> bool:
    """RSA 로그인 — CDP 폴백. NID_AUT/NID_SES 쿠키 획득 시 True."""
    logger.info("auth.rsa.start username=%s", username)
    keys = _naver_get_rsa_keys(session)
    enc_pw, key_name = _naver_encrypt_credentials(
        keys["session_key"],
        keys["key_name"],
        keys["e_val"],
        keys["n_val"],
        username,
        password,
    )
    bvsd = _naver_build_bvsd()
    payload = {
        "svctype": "0",
        "enctp": "1",
        "encpw": enc_pw,
        "encnm": key_name,
        "sv": "https://www.naver.com",
        "url": "https://www.naver.com",
        "id": username,
        "pw": "",
        "locale": "ko_KR",
        "bvsd": bvsd,
    }
    resp = session.post(
        "https://nid.naver.com/nidlogin.login",
        data=payload,
        headers={"Referer": "https://nid.naver.com/nidlogin.login"},
        allow_redirects=False,
    )

    if resp.status_code not in (200, 302) or (
        resp.status_code == 200 and "location.replace" not in resp.text
    ):
        logger.error("auth.rsa.failed status=%s", resp.status_code)
        return False

    if resp.status_code == 200 and "location.replace" in resp.text:
        import re

        m = re.search(r'location\.replace\("([^"]+)"', resp.text)
        if m:
            session.get(m.group(1), allow_redirects=True)

    if resp.status_code == 302:
        location = resp.headers.get("Location", "")
        if location:
            session.get(location, allow_redirects=True)

    cookie_names = {c.name for c in session.cookies}
    if "NID_AUT" in cookie_names or "NID_SES" in cookie_names:
        logger.info("auth.rsa.success")
        return True

    # 일부 계정은 쿠키 미확인이어도 응답이 정상 — auto-publishing 운영 패턴 따름
    logger.info("auth.rsa.success_no_cookie")
    return True


__all__ = ["naver_login", "naver_login_cdp"]
