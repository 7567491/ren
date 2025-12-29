#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频智能匹配引擎 - 基于旁白音频特征匹配背景音乐
支持5维度分析：节奏、能量、情绪、频谱、时长
"""

import json
import librosa
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger


class AudioMatcher:
    """音频智能匹配器"""

    def __init__(self, music_features_cache: Optional[str] = None):
        """
        初始化匹配器

        Args:
            music_features_cache: 音乐特征缓存文件路径
        """
        self.music_features = {}
        if music_features_cache and Path(music_features_cache).exists():
            with open(music_features_cache, 'r', encoding='utf-8') as f:
                self.music_features = json.load(f)

    # ==================== 旁白音频分析 ====================

    def analyze_narration_audio(self, audio_files: List[Path]) -> Dict:
        """
        分析所有旁白音频的综合特征

        Args:
            audio_files: 旁白音频文件列表 [shot_1_audio.mp3, shot_2_audio.mp3, ...]

        Returns:
            综合特征字典
        """
        logger.info(f"🎤 分析 {len(audio_files)} 个旁白音频...")

        all_features = []
        total_duration = 0.0

        for audio_file in audio_files:
            if not audio_file.exists():
                logger.warning(f"⚠️  音频文件不存在: {audio_file}")
                continue

            features = self._extract_narration_features(audio_file)
            all_features.append(features)
            total_duration += features['duration']

        if not all_features:
            logger.error("❌ 未成功分析任何旁白音频")
            return {}

        # 计算综合特征（加权平均）
        combined = self._combine_narration_features(all_features, total_duration)

        logger.success(f"✅ 旁白分析完成: 总时长 {total_duration:.1f}s, 平均语速 {combined['avg_speech_rate']:.1f} syllables/s")
        return combined

    def _extract_narration_features(self, audio_file: Path) -> Dict:
        """
        提取单个旁白音频的特征

        Returns:
            {
                'duration': 时长,
                'rms_energy': RMS能量,
                'zero_crossing_rate': 过零率（语速指标）,
                'spectral_centroid': 频谱质心（音调亮度）,
                'pitch_variance': 音调方差（情绪波动）,
                'speech_rate': 估算语速
            }
        """
        try:
            # 加载音频
            y, sr = librosa.load(str(audio_file), sr=None)

            # 1. 基础特征
            duration = librosa.get_duration(y=y, sr=sr)

            # 2. 能量特征（RMS）
            rms = librosa.feature.rms(y=y)[0]
            rms_mean = float(np.mean(rms))
            rms_std = float(np.std(rms))

            # 3. 过零率（Zero Crossing Rate - 反映语速）
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            zcr_mean = float(np.mean(zcr))

            # 4. 频谱质心（Spectral Centroid - 音调亮度）
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            sc_mean = float(np.mean(spectral_centroid))

            # 5. 音调估算（Pitch）
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:  # 过滤静音帧
                    pitch_values.append(pitch)

            pitch_variance = float(np.var(pitch_values)) if pitch_values else 0.0

            # 6. 估算语速（基于onset检测）
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
            speech_rate = len(onset_frames) / duration if duration > 0 else 0.0

            return {
                'duration': float(duration),
                'rms_energy': rms_mean,
                'rms_std': rms_std,
                'zero_crossing_rate': zcr_mean,
                'spectral_centroid': sc_mean,
                'pitch_variance': pitch_variance,
                'speech_rate': speech_rate,  # onsets per second (近似音节/秒)
            }

        except Exception as e:
            logger.error(f"❌ 分析音频失败 {audio_file.name}: {e}")
            return {'duration': 0.0}

    def _combine_narration_features(self, features_list: List[Dict], total_duration: float) -> Dict:
        """
        合并多个旁白的特征（按时长加权平均）
        """
        if not features_list:
            return {}

        # 按时长加权
        weights = np.array([f['duration'] for f in features_list])
        weights = weights / weights.sum()

        combined = {
            'total_duration': total_duration,
            'avg_rms_energy': float(np.average([f['rms_energy'] for f in features_list], weights=weights)),
            'avg_rms_std': float(np.average([f['rms_std'] for f in features_list], weights=weights)),
            'avg_zcr': float(np.average([f['zero_crossing_rate'] for f in features_list], weights=weights)),
            'avg_spectral_centroid': float(np.average([f['spectral_centroid'] for f in features_list], weights=weights)),
            'avg_pitch_variance': float(np.average([f['pitch_variance'] for f in features_list], weights=weights)),
            'avg_speech_rate': float(np.average([f['speech_rate'] for f in features_list], weights=weights)),
        }

        return combined

    # ==================== 音乐库特征提取 ====================

    def analyze_music_library(self, music_dir: Path, output_cache: Optional[str] = None) -> Dict:
        """
        分析音乐库，提取所有音乐的特征

        Args:
            music_dir: 音乐目录
            output_cache: 输出缓存文件路径

        Returns:
            音乐特征字典 {filename: features}
        """
        logger.info(f"🎵 开始分析音乐库: {music_dir}")

        music_files = list(music_dir.glob('*.mp3')) + list(music_dir.glob('*.wav')) + list(music_dir.glob('*.m4a'))

        if not music_files:
            logger.error(f"❌ 未找到音乐文件: {music_dir}")
            return {}

        features_dict = {}

        for i, music_file in enumerate(music_files, 1):
            logger.info(f"  [{i}/{len(music_files)}] 分析: {music_file.name}")
            features = self._extract_music_features(music_file)
            if features:
                features_dict[music_file.name] = features

        # 保存缓存
        if output_cache:
            cache_path = Path(output_cache)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(features_dict, f, indent=2, ensure_ascii=False)
            logger.success(f"✅ 音乐特征缓存已保存: {cache_path}")

        self.music_features = features_dict
        return features_dict

    def _extract_music_features(self, music_file: Path) -> Optional[Dict]:
        """
        提取单个音乐文件的特征

        Returns:
            {
                'duration': 时长,
                'bpm': 节奏,
                'rms_energy': 平均能量,
                'spectral_centroid': 频谱质心,
                'dynamic_range': 动态范围,
                'beat_strength': 节拍强度
            }
        """
        try:
            # 加载音频（限制时长以加速分析）
            y, sr = librosa.load(str(music_file), sr=22050, duration=60)  # 只分析前60秒

            # 1. 时长
            duration = float(librosa.get_duration(y=y, sr=sr))

            # 2. BPM（节奏）
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo)

            # 3. RMS能量
            rms = librosa.feature.rms(y=y)[0]
            rms_mean = float(np.mean(rms))

            # 4. 频谱质心
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            sc_mean = float(np.mean(spectral_centroid))

            # 5. 动态范围（最大能量 / 最小能量）
            rms_max = float(np.max(rms))
            rms_min = float(np.min(rms[rms > 0])) if np.any(rms > 0) else 0.001
            dynamic_range = rms_max / rms_min

            # 6. 节拍强度
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            beat_strength = float(np.mean(onset_env))

            return {
                'duration': duration,
                'bpm': bpm,
                'rms_energy': rms_mean,
                'spectral_centroid': sc_mean,
                'dynamic_range': dynamic_range,
                'beat_strength': beat_strength,
            }

        except Exception as e:
            logger.error(f"❌ 分析音乐失败 {music_file.name}: {e}")
            return None

    # ==================== 智能匹配算法 ====================

    def calculate_match_score(
        self,
        narration_features: Dict,
        music_name: str
    ) -> Tuple[float, Dict]:
        """
        计算旁白与音乐的匹配分数（0-1）

        Args:
            narration_features: 旁白综合特征
            music_name: 音乐文件名

        Returns:
            (总分, 各维度分数详情)
        """
        if music_name not in self.music_features:
            return 0.0, {}

        music_feat = self.music_features[music_name]

        # 1. 节奏匹配（Speech Rate vs BPM）
        # 语速转BPM：speech_rate * 60 (假设1 onset ≈ 1拍)
        narration_bpm = narration_features['avg_speech_rate'] * 60
        music_bpm = music_feat['bpm']

        # 计算BPM比例（理想是1:1或1:2）
        bpm_ratio = narration_bpm / music_bpm if music_bpm > 0 else 0
        if bpm_ratio > 1:
            bpm_ratio = 1 / bpm_ratio

        # 允许1:1或1:2的关系
        rhythm_score = max(bpm_ratio, bpm_ratio * 2 if bpm_ratio * 2 <= 1 else 0)
        rhythm_score = min(rhythm_score, 1.0)

        # 2. 能量匹配（RMS）
        narration_energy = narration_features['avg_rms_energy']
        music_energy = music_feat['rms_energy']

        # 归一化能量差异（期望差异小于50%）
        energy_diff = abs(narration_energy - music_energy) / max(narration_energy, music_energy, 0.01)
        energy_score = max(0, 1 - energy_diff)

        # 3. 动态范围匹配（情绪波动）
        narration_dynamics = narration_features['avg_rms_std']
        music_dynamics = music_feat['dynamic_range']

        # 归一化后计算相似度
        dynamics_score = 1 - min(abs(narration_dynamics - music_dynamics / 10) / 0.5, 1.0)

        # 4. 频谱互补性（避免冲突）
        # 人声主要在 300-3000Hz，音乐最好偏低频或高频
        narration_sc = narration_features['avg_spectral_centroid']
        music_sc = music_feat['spectral_centroid']

        # 如果音乐频谱质心远离人声范围，得分更高
        spectral_diff = abs(narration_sc - music_sc)
        spectral_score = min(spectral_diff / 2000, 1.0)  # 差异越大越好

        # 5. 时长适配（减少循环次数）
        total_duration = narration_features['total_duration']
        music_duration = music_feat['duration']

        # 计算需要循环的次数
        loops_needed = total_duration / music_duration if music_duration > 0 else 10
        duration_score = 1 / (1 + abs(loops_needed - 1))  # 接近1次循环得分最高

        # 加权计算总分
        weights = {
            'rhythm': 0.40,      # 节奏最重要
            'energy': 0.214,     # 能量次之
            'dynamics': 0.171,   # 动态范围
            'spectral': 0.129,   # 频谱互补
            'duration': 0.086,   # 时长适配
        }

        total_score = (
            rhythm_score * weights['rhythm'] +
            energy_score * weights['energy'] +
            dynamics_score * weights['dynamics'] +
            spectral_score * weights['spectral'] +
            duration_score * weights['duration']
        )

        details = {
            'rhythm_score': round(rhythm_score, 3),
            'energy_score': round(energy_score, 3),
            'dynamics_score': round(dynamics_score, 3),
            'spectral_score': round(spectral_score, 3),
            'duration_score': round(duration_score, 3),
            'total_score': round(total_score, 3),
            'narration_bpm_est': round(narration_bpm, 1),
            'music_bpm': round(music_bpm, 1),
            'loops_needed': round(loops_needed, 2),
        }

        return total_score, details

    def rank_music_candidates(
        self,
        narration_features: Dict,
        top_k: int = 5
    ) -> List[Tuple[str, float, Dict]]:
        """
        对所有音乐进行排序，返回Top-K候选

        Returns:
            [(music_name, score, details), ...]
        """
        if not self.music_features:
            logger.error("❌ 音乐特征库为空，请先运行预处理")
            return []

        candidates = []

        for music_name in self.music_features.keys():
            score, details = self.calculate_match_score(narration_features, music_name)
            candidates.append((music_name, score, details))

        # 按分数降序排序
        candidates.sort(key=lambda x: x[1], reverse=True)

        # 返回Top-K
        return candidates[:top_k]

    def format_candidates_for_llm(
        self,
        candidates: List[Tuple[str, float, Dict]]
    ) -> str:
        """
        格式化候选音乐列表，用于DeepSeek推理
        """
        lines = []
        for i, (music_name, score, details) in enumerate(candidates, 1):
            lines.append(f"{i}. {music_name}")
            lines.append(f"   总分: {score:.2f}")
            lines.append(f"   节奏匹配: {details['rhythm_score']:.2f} (旁白≈{details['narration_bpm_est']}BPM vs 音乐{details['music_bpm']}BPM)")
            lines.append(f"   能量匹配: {details['energy_score']:.2f}")
            lines.append(f"   动态范围: {details['dynamics_score']:.2f}")
            lines.append(f"   频谱互补: {details['spectral_score']:.2f}")
            lines.append(f"   时长适配: {details['duration_score']:.2f} (需循环{details['loops_needed']}次)")
            lines.append("")

        return "\n".join(lines)


# ==================== 便捷函数 ====================

def preprocess_music_library(music_dir: str, output_cache: str = "resource/music_features.json"):
    """
    预处理音乐库（一次性操作）

    Usage:
        python -c "from py.services.audio_matcher import preprocess_music_library; preprocess_music_library('./resource/songs')"
    """
    matcher = AudioMatcher()
    features = matcher.analyze_music_library(Path(music_dir), output_cache)

    logger.success(f"✅ 预处理完成！共分析 {len(features)} 首音乐")
    logger.info(f"💾 特征缓存: {output_cache}")

    return features


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        music_dir = sys.argv[1]
        output_cache = sys.argv[2] if len(sys.argv) > 2 else "resource/music_features.json"
        preprocess_music_library(music_dir, output_cache)
    else:
        logger.info("用法: python py/services/audio_matcher.py <music_dir> [output_cache]")
        logger.info("示例: python py/services/audio_matcher.py ./resource/songs ./resource/music_features.json")
