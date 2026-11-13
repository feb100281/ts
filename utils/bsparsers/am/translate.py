"""Перевод назначений по словарю шаблонов: числа заменяются на #, перевод хранится один раз на шаблон."""

import hashlib
import re

NUM = re.compile(r"\d+(?:[.,]\d+)*")


def template(text: str) -> tuple[str, list[str]]:
    nums = NUM.findall(text or "")
    return NUM.sub("#", text or ""), nums


def key_of(tpl: str) -> str:
    return hashlib.sha1(tpl.encode("utf-8")).hexdigest()


def fill(translation: str, nums: list[str]) -> str:
    """Подставить числа оригинала вместо # по порядку. Если # не совпадают по количеству — без подстановки."""
    if translation.count("#") != len(nums):
        return translation
    it = iter(nums)
    return re.sub("#", lambda _: next(it), translation)
