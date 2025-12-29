#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VideoComposer 行为测试（聚焦字幕定位逻辑）。"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "py"))

from services.video_composer import VideoComposer


def test_subtitle_position_respects_safe_padding():
    """安全边距应当把字幕整体抬高。"""
    base_y = VideoComposer._compute_subtitle_position(
        video_height=1080,
        clip_height=120,
        bottom_margin=60,
        offset_ratio=0,
        safe_padding=0,
    )
    padded_y = VideoComposer._compute_subtitle_position(
        video_height=1080,
        clip_height=120,
        bottom_margin=60,
        offset_ratio=0,
        safe_padding=40,
    )

    assert padded_y == base_y - 40


def test_subtitle_position_uses_padded_height_for_offset():
    """行偏移需要考虑文字高度与安全边距的总和。"""
    y_pos = VideoComposer._compute_subtitle_position(
        video_height=1080,
        clip_height=120,
        bottom_margin=60,
        offset_ratio=0.5,
        safe_padding=40,
    )

    # 1080 - 120 - (60 + 40) = 860; 再减去 0.5 * (120 + 40) = 80
    assert y_pos == 780


def test_subtitle_position_never_negative():
    """极端配置下也需要兜底到 0。"""
    y_pos = VideoComposer._compute_subtitle_position(
        video_height=400,
        clip_height=390,
        bottom_margin=80,
        offset_ratio=1.0,
        safe_padding=20,
    )

    assert y_pos == 0
