#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 CTA 生成脚本
基于 logo 先生成图像，再生成 5 秒 I2V 片尾动画
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yaml
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent))
from services.rate_limiter import RateLimiter


load_dotenv()

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"
CONFIG: Dict = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f) or {}

RUNTIME_CONFIG = CONFIG.get("runtime", {})
POLLING_CONFIG = RUNTIME_CONFIG.get("polling", {})
IMAGE_DEFAULTS = RUNTIME_CONFIG.get("image_generation", {})
VIDEO_DEFAULTS = RUNTIME_CONFIG.get("video_generation", {})

IMAGE_MODEL_CONFIG = CONFIG.get("models", {}).get("image", {}).get("available", {})
VIDEO_MODEL_CONFIG = CONFIG.get("models", {}).get("video", {}).get("available", {})
CURRENT_IMAGE_MODEL = CONFIG.get("models", {}).get("image", {}).get("current", "kling-image-o1")
CURRENT_VIDEO_MODEL = CONFIG.get("models", {}).get("video", {}).get("current", "wan-2.5-i2v")

WAVESPEED_CONFIG = CONFIG.get("wavespeed", {})
WAVESPEED_BASE = WAVESPEED_CONFIG.get("base_url", "https://api.wavespeed.ai")
WAVESPEED_API_KEY = (CONFIG.get("api", {}) or {}).get("wavespeed_key", "") or ""

if not WAVESPEED_API_KEY:
    if sys.stdin.isatty():
        print("🔑 Wavespeed API 密钥未在配置中找到，请输入：")
        while not WAVESPEED_API_KEY:
            try:
                user_key = input("Wavespeed API Key: ").strip()
            except EOFError:
                user_key = ""
            if user_key:
                WAVESPEED_API_KEY = user_key
            else:
                print("❌ Wavespeed API Key 不能为空，请重新输入。")
    else:
        raise RuntimeError("缺少 Wavespeed API Key，请在 user.yaml/config.yaml 的 api.wavespeed_key 中配置或通过前端输入。")

rate_limits = CONFIG.get("rate_limits", {})
image_limiter = RateLimiter(
    max_requests_per_minute=rate_limits.get("image_generation", {}).get("max_requests_per_minute"),
    max_requests_per_day=rate_limits.get("image_generation", {}).get("max_requests_per_day"),
    name="image",
)
video_limiter = RateLimiter(
    max_requests_per_minute=rate_limits.get("video_generation", {}).get("max_requests_per_minute"),
    max_requests_per_day=rate_limits.get("video_generation", {}).get("max_requests_per_day"),
    name="video",
)

POLLING_INTERVAL = POLLING_CONFIG.get("check_interval_seconds", 10)
# 至少等待5分钟，避免图像生成超时
MAX_WAIT_IMAGE = max(POLLING_CONFIG.get("max_wait_seconds", {}).get("image", 120), 300)
MAX_WAIT_VIDEO = max(POLLING_CONFIG.get("max_wait_seconds", {}).get("video", 600), 600)
MAX_NETWORK_RETRIES = POLLING_CONFIG.get("max_network_retries", 5)
BACKOFF_SECONDS = POLLING_CONFIG.get("backoff_seconds", 5)
MAX_BACKOFF_SECONDS = POLLING_CONFIG.get("max_backoff_seconds", 30)

OUTPUT_BASE = Path(CONFIG.get("workflow", {}).get("output_base", "./output"))
WORK_DIR = OUTPUT_BASE / "cta"
WORK_DIR.mkdir(parents=True, exist_ok=True)

CTA_SCENES: List[Dict[str, str]] = [
    {
        "id": "edge-awakens",
        "title": "边缘觉醒，智能无界",
        "cta": "立即体验推理云",
        "visual": "night sky dust converging, Akamai logo lights up at center with pale blue energy ring, slight pull back reveal",
        "motion": "smooth pull-back from close-up logo to full frame, keep particles shimmering",
    },
    {
        "id": "4200-nodes",
        "title": "全球 4200+ 节点，毫秒触达智能",
        "cta": "一键上线边缘推理",
        "visual": "black canvas with star map nodes blinking and linking into mesh, logo hovering in center, star chains collapse into logo",
        "motion": "gentle orbit with grid convergence toward the logo, end on static lock",
    },
    {
        "id": "cost-86",
        "title": "AI 在边缘，成本降 86%",
        "cta": "立即测算节省",
        "visual": "large glowing 86% digits made of flowing particles dissolve into logo, logo peaks in brightness",
        "motion": "camera drift in as particles stream toward logo, settle on steady hero shot",
    },
    {
        "id": "global-local",
        "title": "分布全球，智能本地",
        "cta": "预约边缘部署演示",
        "visual": "thin light horizon cuts through black, arc rises like Earth curve, logo lifts from arc",
        "motion": "slow upward crane from horizon line to centered logo, hold to finish",
    },
    {
        "id": "edge-now",
        "title": "边缘即刻，云端不再等待",
        "cta": "立即开跑",
        "visual": "deep dark background with fast blue vertical streaks forming speed lines, streaks slow down as logo locks center",
        "motion": "tracking ease-out as streaks decelerate, final static logo with clean breathing space",
    },
]


def log(message: str, level: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")


def upload_logo() -> str:
    upload_cfg = RUNTIME_CONFIG.get("image_upload", {})
    endpoint = upload_cfg.get("endpoint")
    api_key = upload_cfg.get("api_key")
    if not endpoint or not api_key:
        raise RuntimeError("缺少图床配置 runtime.image_upload")

    # 优先使用用户指定参考图
    preferred = ROOT / "resource" / "logo" / "aka_w.png"
    logo_path = preferred if preferred.exists() else ROOT / "resource" / "logo" / "aka_transparent.png"
    if not logo_path.exists():
        fallback = ROOT / "resource" / "logo" / "aka_outline_white.png"
        logo_path = fallback if fallback.exists() else logo_path

    log(f"上传 logo 用于参考图: {logo_path}")
    image_data = logo_path.read_bytes()
    encoded = base64.b64encode(image_data).decode("utf-8")

    params = {"key": api_key}
    payload = {"image": encoded}
    response = requests.post(endpoint, params=params, data=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result.get("success") and "data" in result:
        url = result["data"].get("url")
        if not url:
            raise ValueError("图床返回缺少URL")
        log(f"Logo 已上传: {url}")
        return url
    raise ValueError(f"图床上传失败: {result}")


def get_reference_url() -> Optional[str]:
    # 允许直接指定公网URL，优先级：config.yaml > 环境变量 > 上传
    logo_cfg = CONFIG.get("logo", {})
    for key in ("url", "logo_url", "logo_uri"):
        cfg_url = logo_cfg.get(key)
        if cfg_url:
            log(f"使用 config.yaml 中的 logo URL ({key}): {cfg_url}")
            return cfg_url

    env_url = os.getenv("CTA_LOGO_URL")
    if env_url:
        log(f"使用 CTA_LOGO_URL 作为参考图: {env_url}")
        return env_url

    # 固定兜底 URL（用户提供）
    default_url = "https://s.linapp.fun/Aka.jpg"
    if default_url:
        log(f"使用内置默认参考图: {default_url}")
        return default_url

    try:
        return upload_logo()
    except Exception as exc:
        log(f"参考图上传失败，将使用纯文本: {exc}", "WARN")
        return None


def parse_api_response(response_json: Dict, context: str = "API调用") -> Dict:
    if os.getenv("DEBUG") == "1":
        log(f"[DEBUG] {context}: {json.dumps(response_json, ensure_ascii=False)[:200]}...")

    if "code" in response_json:
        if response_json.get("code") != 200:
            message = response_json.get("message", "未知错误")
            raise RuntimeError(f"{context} 失败: {message}")
        return response_json.get("data", response_json)
    return response_json


def wait_for_result(task_id: str, label: str, max_wait: int) -> str:
    url = f"{WAVESPEED_BASE}/api/v3/predictions/{task_id}/result"
    headers = {"Authorization": f"Bearer {WAVESPEED_API_KEY}"}

    start = time.time()
    retries = 0

    while time.time() - start < max_wait:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = parse_api_response(response.json(), f"查询{label}")
            status = result.get("status")
            if status == "succeeded":
                output_url = result.get("output") or result.get("url") or result.get("video") or result.get("image")
                if isinstance(output_url, list):
                    output_url = output_url[-1]
                if not output_url:
                    raise RuntimeError(f"{label} 返回缺少结果 URL")
                return output_url
            if status in {"failed", "canceled"}:
                raise RuntimeError(f"{label} 任务失败: {result}")

            time.sleep(POLLING_INTERVAL)
            retries = 0
        except requests.exceptions.RequestException as exc:
            retries += 1
            if retries > MAX_NETWORK_RETRIES:
                raise RuntimeError(f"{label} 轮询超出最大重试: {exc}")
            wait = min(BACKOFF_SECONDS * retries, MAX_BACKOFF_SECONDS)
            log(f"网络异常，{wait} 秒后重试 ({label})")
            time.sleep(wait)

    raise TimeoutError(f"等待 {label} 超时")


def generate_image(prompt: str, shot_id: int, shot_total: int, reference_url: Optional[str]) -> str:
    model = IMAGE_MODEL_CONFIG.get(CURRENT_IMAGE_MODEL)
    if not model:
        raise RuntimeError(f"未找到图像模型: {CURRENT_IMAGE_MODEL}")

    url = f"{WAVESPEED_BASE}{model['endpoint']}"
    headers = {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict = {
        "prompt": prompt,
        "enable_prompt_expansion": IMAGE_DEFAULTS.get("enable_prompt_expansion", False),
        "seed": IMAGE_DEFAULTS.get("seed", -1),
    }
    payload.update(model.get("params", {}))

    if reference_url and model.get("support_reference"):
        payload["images"] = [reference_url]

    log(f"[图像] {shot_id}/{shot_total} 提交 {CURRENT_IMAGE_MODEL}")
    image_limiter.acquire()
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = parse_api_response(response.json(), "图像生成")
    task_id = result.get("id")
    if not task_id:
        raise RuntimeError("图像任务缺少ID")

    image_url = wait_for_result(task_id, "图像", MAX_WAIT_IMAGE)
    image_path = WORK_DIR / f"{shot_id:02d}_image.png"
    download_file(image_url, image_path)
    log(f"[图像] 完成: {image_path}")
    return image_url


def generate_video(image_url: str, prompt: str, shot_id: int, shot_total: int, resolution: str = "720p") -> Path:
    model = VIDEO_MODEL_CONFIG.get(CURRENT_VIDEO_MODEL)
    if not model:
        raise RuntimeError(f"未找到视频模型: {CURRENT_VIDEO_MODEL}")

    url = f"{WAVESPEED_BASE}{model['endpoint']}"
    headers = {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict = {
        "prompt": prompt,
        "resolution": resolution,
        "duration": VIDEO_DEFAULTS.get("duration_seconds", 5),
        "enable_prompt_expansion": VIDEO_DEFAULTS.get("enable_prompt_expansion", False),
        "seed": VIDEO_DEFAULTS.get("seed", -1),
    }

    if model.get("type") == "i2v":
        payload["image"] = image_url

    log(f"[视频] {shot_id}/{shot_total} 提交 {CURRENT_VIDEO_MODEL} @ {resolution}")
    video_limiter.acquire()
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = parse_api_response(response.json(), "视频生成")
    task_id = result.get("id")
    if not task_id:
        raise RuntimeError("视频任务缺少ID")

    video_url = wait_for_result(task_id, "视频", MAX_WAIT_VIDEO)
    video_path = WORK_DIR / f"{shot_id:02d}_video.mp4"
    download_file(video_url, video_path)
    log(f"[视频] 完成: {video_path}")
    return video_path


def download_file(url: str, target: Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    target.write_bytes(response.content)


def build_image_prompt(scene: Dict[str, str]) -> str:
    base_style = (
        "black or starry night background, neon blue and white highlights, high contrast, "
        "clean negative space for CTA text in Chinese, subtle particles and glow"
    )
    text_layer = f"display Chinese slogan '{scene['title']}' and CTA '{scene['cta']}' in crisp sans-serif white or azure on corners"
    return (
        f"Akamai inference cloud logo centered, {scene['visual']}, {base_style}, {text_layer}, "
        "professional advertising frame"
    )


def build_video_prompt(scene: Dict[str, str]) -> str:
    return (
        f"Use the provided image as reference. {scene['motion']}. "
        "Preserve black or night-sky background, neon rim light, Chinese CTA text stays sharp in white/blue. "
        "Cinematic lighting, smooth easing, no additional objects beyond logo and minimal particles."
    )


def run() -> None:
    log("开始生成 5 个 CTA 片尾")
    reference_url = get_reference_url()

    results: List[Dict[str, str]] = []

    for idx, scene in enumerate(CTA_SCENES, 1):
        try:
            image_prompt = build_image_prompt(scene)
            video_prompt = build_video_prompt(scene)

            image_url = generate_image(image_prompt, idx, len(CTA_SCENES), reference_url)
            video_path = generate_video(image_url, video_prompt, idx, len(CTA_SCENES))

            results.append(
                {
                    "id": scene["id"],
                    "title": scene["title"],
                    "cta": scene["cta"],
                    "image_prompt": image_prompt,
                    "video_prompt": video_prompt,
                    "image_url": image_url,
                    "video_file": str(video_path),
                }
            )

        except Exception as exc:
            log(f"场景 {scene['id']} 生成失败: {exc}", "ERROR")

    summary_file = WORK_DIR / "cta_results.json"
    summary_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"完成，结果清单: {summary_file}")


if __name__ == "__main__":
    run()
