#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Character library storage tests."""

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "py"))

from services import character_library  # noqa: E402


@pytest.fixture(autouse=True)
def _temp_library(tmp_path):
    original_path = character_library.CHARACTER_LIBRARY_FILE
    test_path = tmp_path / 'library.json'
    character_library.set_character_library_file(test_path)
    yield
    character_library.set_character_library_file(original_path)


def test_upsert_creates_and_lists_reference():
    record = character_library.upsert_reference(
        name='红色旗袍女主',
        image_url='https://example.com/a.png',
        description='测试人物'
    )
    assert record['id'].startswith('gallery-')
    assert record['name'] == '红色旗袍女主'

    all_refs = character_library.list_references()
    assert len(all_refs) == 1
    assert all_refs[0]['image_url'] == 'https://example.com/a.png'


def test_upsert_updates_existing_by_url():
    first = character_library.upsert_reference(
        name='角色A',
        image_url='https://example.com/same.png',
        description='desc'
    )
    second = character_library.upsert_reference(
        name='角色B',
        image_url='https://example.com/same.png',
        description='new desc'
    )
    assert first['id'] == second['id']
    refs = character_library.list_references()
    assert refs[0]['name'] == '角色B'
    assert refs[0]['description'] == 'new desc'


def test_list_ordering_is_descending_by_created_at():
    character_library.upsert_reference('1', 'https://example.com/1.png', 'a')
    character_library.upsert_reference('2', 'https://example.com/2.png', 'b')
    refs = character_library.list_references()
    assert refs[0]['image_url'] == 'https://example.com/2.png'
