"""수동 NID_AUT/NID_SES 쿠키 주입 → SessionManager .pkl 캐시 저장.

Chrome 136+ App-Bound Encryption v20 으로 인해 CDP 자동 로그인이
임시 사본·원본 user-data-dir 어느 경로로도 NID_AUT 를 추출하지 못하는
환경에서, 사용자가 dev tools 로 복사한 쿠키 값을 직접 주입하는 PoC 도구.

사용:
    # 1. Chrome Profile 4 → blog.naver.com → F12 → Application → Storage
    #    → Cookies → https://www.naver.com → NID_AUT, NID_SES 의 'Value' 복사
    # 2. 아래 명령 실행 (값은 입력 프롬프트에 붙여넣기 — 화면 표시 X)
    python scripts/inject_naver_cookies.py --session-name naver_blog_taq87641

    # 다중 채널 운영 시 channel UUID 또는 blog_id 로 분리:
    python scripts/inject_naver_cookies.py --session-name naver_blog_cfi9037

검증:
    python -c "from domain.publishing.session import SessionManager; \\
               sm=SessionManager('naver_blog_taq87641'); sm.load(); \\
               print('OK', sm.has_login_cookie())"

주의:
    - NID_AUT 는 영구 쿠키, NID_SES 는 약 24시간 유효. 만료 시 재주입 필요.
    - 본 도구는 PoC. 운영 자동화는 RSA 폴백 또는 Chrome 자동화 별도 검토.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import sys

from domain.publishing.session import SessionManager


def _read_cookie(name: str) -> str:
    value = getpass.getpass(f"{name} 값 (입력은 화면에 표시되지 않음): ").strip()
    if not value:
        raise SystemExit(f"{name} 입력이 비어 있습니다")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="수동 NID_AUT/NID_SES 쿠키 주입 — Chrome ABE v20 우회 PoC",
    )
    parser.add_argument(
        "--session-name",
        required=True,
        help="SessionManager name. 예: naver_blog_taq87641 (publisher 기본 패턴)",
    )
    parser.add_argument(
        "--nnb",
        default=None,
        help="(선택) NNB 쿠키 값. 미지정 시 누락 — 일부 케이스에서 RabbitWrite 호환 위해 필요",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("scripts.inject_naver_cookies")

    nid_aut = _read_cookie("NID_AUT")
    nid_ses = _read_cookie("NID_SES")

    sm = SessionManager(args.session_name)
    # SessionManager.session.cookies.set(name, value, domain) — domain 은 .naver.com 통일.
    # save() 가 {name: value} dict 로 직렬화하므로 domain 정보는 load() 시 _NAVER_DOMAINS 에
    # 다시 펴진다 (session.py 의 load 로직 참조).
    sm.session.cookies.set("NID_AUT", nid_aut, domain=".naver.com")
    sm.session.cookies.set("NID_SES", nid_ses, domain=".naver.com")
    if args.nnb:
        sm.session.cookies.set("NNB", args.nnb, domain=".naver.com")

    if not sm.has_login_cookie():
        logger.error("inject.failed — has_login_cookie False (값이 잘못됐을 수 있음)")
        return 1

    sm.save()
    logger.info(
        "inject.success session=%s path=%s n_cookies=%d",
        args.session_name,
        sm.cookie_path,
        len(sm.session.cookies),
    )
    print(
        "\n다음 단계:\n"
        "  1. config/.env 에 PUBLISHING_ENABLED=true 설정\n"
        "  2. python scripts/publish.py --slug <slug> --channel-id <uuid> "
        "--keyword '<키워드>' --dry-run\n"
        "  3. dry-run OK 면 --dry-run 제거하고 실 발행"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
