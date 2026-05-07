"""BlogChannel 모델 단위 테스트."""

from __future__ import annotations

import pytest

from domain.blog_channel.model import BlogChannel, BlogChannelDuplicateError


def test_default_is_default_false() -> None:
    c = BlogChannel(
        name="메인", blog_id="myblog123", homepage_url="https://blog.naver.com/myblog123"
    )
    assert c.is_default is False
    assert c.id is None


def test_name_min_length_enforced() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BlogChannel(name="", blog_id="x", homepage_url="https://blog.naver.com/x")


def test_blog_channel_duplicate_error_is_exception() -> None:
    err = BlogChannelDuplicateError("이미 존재하는 별칭")
    assert isinstance(err, Exception)
    assert "이미 존재" in str(err)
