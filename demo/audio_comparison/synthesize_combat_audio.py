#!/usr/bin/env python3
"""
음성 + 전장 노이즈 합성 스크립트
- 깨끗한 음성 + JSON 기반 전장 효과음 → 노이즈 포함 음성
- SNR 자동 조정
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
import json
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

class CombatAudioSynthesizer:
    def __init__(self, target_sr=16000):
        self.target_sr = target_sr
        print(f"🎖️  Combat Audio Synthesizer")
        print(f"   Sample rate: {target_sr} Hz")
    
    def load_audio(self, file_path):
        """오디오 로드"""
        audio, _ = librosa.load(file_path, sr=self.target_sr, mono=True)
        return audio
    
    def load_effect(self, file_path, target_length):
        """효과음 로드 및 길이 맞추기"""
        audio, _ = librosa.load(file_path, sr=self.target_sr, mono=True)
        
        if len(audio) < target_length:
            repeats = int(np.ceil(target_length / len(audio)))
            audio = np.tile(audio, repeats)[:target_length]
        else:
            audio = audio[:target_length]
        
        return audio
    
    def apply_fade(self, audio, fade_in_sec=1.0, fade_out_sec=1.0):
        """페이드 인/아웃"""
        audio_faded = audio.copy()
        
        fade_in_samples = int(fade_in_sec * self.target_sr)
        fade_out_samples = int(fade_out_sec * self.target_sr)
        
        if fade_in_samples > 0 and fade_in_samples < len(audio_faded):
            fade_in_curve = np.linspace(0, 1, fade_in_samples)
            audio_faded[:fade_in_samples] *= fade_in_curve
        
        if fade_out_samples > 0 and fade_out_samples < len(audio_faded):
            fade_out_curve = np.linspace(1, 0, fade_out_samples)
            audio_faded[-fade_out_samples:] *= fade_out_curve
        
        return audio_faded
    
    def add_impulse(self, base_audio, impulse_audio, timing_sec, volume=1.0):
        """임펄스 추가"""
        start_sample = int(timing_sec * self.target_sr)
        
        if start_sample >= len(base_audio):
            return base_audio
        
        end_sample = min(start_sample + len(impulse_audio), len(base_audio))
        impulse_length = end_sample - start_sample
        
        base_audio[start_sample:end_sample] += impulse_audio[:impulse_length] * volume
        
        return base_audio
    
    def add_segment(self, base_audio, segment_audio, start_sec, duration_sec,
                    volume=1.0, fade_in_sec=1.0, fade_out_sec=1.0):
        """세그먼트 추가"""
        start_sample = int(start_sec * self.target_sr)
        segment_length = int(duration_sec * self.target_sr)
        
        if start_sample >= len(base_audio):
            return base_audio
        
        segment = segment_audio[:segment_length]
        if len(segment) < segment_length:
            repeats = int(np.ceil(segment_length / len(segment)))
            segment = np.tile(segment, repeats)[:segment_length]
        
        segment = self.apply_fade(segment, fade_in_sec, fade_out_sec)
        
        end_sample = min(start_sample + len(segment), len(base_audio))
        actual_length = end_sample - start_sample
        base_audio[start_sample:end_sample] += segment[:actual_length] * volume
        
        return base_audio
    
    def scale_config_to_duration(self, config, target_duration):
        """JSON 설정을 목표 duration에 맞춰 스케일링"""
        original_duration = config.get('duration', 20)
        scale_factor = target_duration / original_duration
        
        scaled_config = config.copy()
        scaled_config['duration'] = target_duration
        scaled_config['effects'] = {}
        
        for effect_name, effect_config in config['effects'].items():
            scaled_effect = effect_config.copy()
            
            if effect_config['type'] == 'impulse':
                original_timings = effect_config['timings']
                scaled_timings = [t * scale_factor for t in original_timings]
                scaled_timings = [t for t in scaled_timings if t < target_duration - 1]
                scaled_effect['timings'] = scaled_timings
                
            elif effect_config['type'] == 'segment':
                scaled_effect['start'] = effect_config['start'] * scale_factor
                scaled_effect['duration'] = min(
                    effect_config['duration'] * scale_factor,
                    target_duration - scaled_effect['start'] - 1
                )
            
            scaled_config['effects'][effect_name] = scaled_effect
        
        return scaled_config
    
    def generate_noise_from_config(self, config, effects_dir, duration):
        """JSON 설정 기반으로 노이즈 생성"""
        # Duration에 맞춰 스케일링
        if duration != config.get('duration', 20):
            config = self.scale_config_to_duration(config, duration)
        
        # 노이즈 베이스 생성
        noise = np.zeros(int(duration * self.target_sr), dtype=np.float32)
        
        # 효과음 추가
        for effect_name, effect_config in config['effects'].items():
            effect_path = effects_dir / effect_config['file']
            effect_type = effect_config['type']
            
            if effect_type == 'continuous':
                effect_audio = self.load_effect(effect_path, len(noise))
                effect_faded = self.apply_fade(
                    effect_audio,
                    fade_in_sec=effect_config.get('fade_in', 1.0),
                    fade_out_sec=effect_config.get('fade_out', 1.0)
                )
                noise += effect_faded * effect_config['volume']
                
            elif effect_type == 'segment':
                effect_audio = self.load_effect(
                    effect_path,
                    target_length=int(effect_config['duration'] * self.target_sr)
                )
                
                noise = self.add_segment(
                    noise, effect_audio,
                    start_sec=effect_config['start'],
                    duration_sec=effect_config['duration'],
                    volume=effect_config['volume'],
                    fade_in_sec=effect_config.get('fade_in', 2.0),
                    fade_out_sec=effect_config.get('fade_out', 2.0)
                )
                
            elif effect_type == 'impulse':
                effect_audio = self.load_effect(effect_path, len(noise))
                
                for timing in effect_config['timings']:
                    noise = self.add_impulse(noise, effect_audio, timing, effect_config['volume'])
        
        return noise
    
    def synthesize(self, clean_speech_path, noise_config, effects_dir, 
                   output_path, target_snr_db=10):
        """
        음성 + 노이즈 합성
        
        Args:
            clean_speech_path: 깨끗한 음성 경로
            noise_config: 노이즈 JSON 설정
            effects_dir: 효과음 디렉토리
            output_path: 출력 경로
            target_snr_db: 목표 SNR (dB)
        """
        print(f"\n🎬 Synthesizing: {Path(clean_speech_path).name}")
        
        # 1. 음성 로드
        clean_speech = self.load_audio(clean_speech_path)
        speech_duration = len(clean_speech) / self.target_sr
        print(f"   Speech duration: {speech_duration:.2f} sec")
        
        # 2. 노이즈 생성 (음성 길이에 맞춰)
        print(f"   Generating noise: {noise_config['name']}")
        noise = self.generate_noise_from_config(noise_config, effects_dir, speech_duration)
        
        # 3. 길이 맞추기
        min_length = min(len(clean_speech), len(noise))
        clean_speech = clean_speech[:min_length]
        noise = noise[:min_length]
        
        # 4. SNR 조정
        speech_power = np.mean(clean_speech ** 2)
        noise_power = np.mean(noise ** 2)
        
        if noise_power > 0:
            # 목표 SNR 계산: SNR = 10 * log10(P_signal / P_noise)
            # → P_noise = P_signal / 10^(SNR/10)
            target_noise_power = speech_power / (10 ** (target_snr_db / 10))
            noise_scale = np.sqrt(target_noise_power / noise_power)
            noise = noise * noise_scale
            
            actual_snr = 10 * np.log10(speech_power / np.mean(noise ** 2))
            print(f"   Target SNR: {target_snr_db} dB")
            print(f"   Actual SNR: {actual_snr:.1f} dB")
        
        # 5. 합성
        noisy_speech = clean_speech + noise
        
        # 6. 정규화 (클리핑 방지)
        max_val = np.max(np.abs(noisy_speech))
        if max_val > 0.95:
            noisy_speech = noisy_speech / max_val * 0.9
            print(f"   Normalized to prevent clipping (peak: {max_val:.2f})")
        
        # 7. 저장
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, noisy_speech, self.target_sr)
        
        print(f"   ✅ Saved: {output_path}")
        
        return noisy_speech

def batch_synthesize(clean_dir, config_file, effects_dir, output_dir, target_snr_db=10):
    """
    디렉토리 내 모든 음성 파일에 노이즈 합성
    
    Args:
        clean_dir: 깨끗한 음성 디렉토리
        config_file: 사용할 시나리오 JSON 파일 경로
        effects_dir: 효과음 디렉토리
        output_dir: 출력 디렉토리
        target_snr_db: 목표 SNR (dB)
    """
    clean_dir = Path(clean_dir)
    config_file = Path(config_file)
    effects_dir = Path(effects_dir)
    output_dir = Path(output_dir)
    
    # JSON 설정 로드
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        noise_config = json.load(f)
    
    # 음성 파일 목록
    audio_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(clean_dir.glob(f'*{ext}'))
    
    if not audio_files:
        print(f"⚠️  No audio files found in {clean_dir}")
        return
    
    print("="*60)
    print("🎖️  Combat Audio Synthesis")
    print("="*60)
    print(f"Clean speech: {clean_dir}")
    print(f"Scenario: {noise_config['name']}")
    print(f"Description: {noise_config['description']}")
    print(f"Files: {len(audio_files)}")
    print(f"Target SNR: {target_snr_db} dB")
    print("="*60)
    
    # 합성기 초기화
    synthesizer = CombatAudioSynthesizer(target_sr=16000)
    
    # 배치 처리
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}]")
        print("="*60)
        
        # 출력 파일명: 원본명_시나리오명_snrXXdb.wav
        output_filename = f"{audio_file.stem}_{noise_config['name']}_snr{target_snr_db}db.wav"
        output_path = output_dir / output_filename
        
        try:
            synthesizer.synthesize(
                clean_speech_path=audio_file,
                noise_config=noise_config,
                effects_dir=effects_dir,
                output_path=output_path,
                target_snr_db=target_snr_db
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("🎉 Batch synthesis complete!")
    print("="*60)
    print(f"\n📂 Output directory: {output_dir}")

# ==================== 메인 ====================
if __name__ == "__main__":
    
    # ===== 여기만 수정하세요! =====
    
    # 1. 입력/출력 경로
    CLEAN_SPEECH_DIR = "demo/audio_comparison/samples/clean_speech"
    OUTPUT_DIR = "demo/audio_comparison/samples/noisy"
    
    # 2. 시나리오 선택 (JSON 파일)
    # 추천: final4_multi_heli (다중 헬기, 균형잡힌 전투)
    SCENARIO_CONFIG = "demo/audio_comparison/scenario_configs/final4_multi_heli.json"
    
    # 다른 옵션들:
    # SCENARIO_CONFIG = "demo/audio_comparison/scenario_configs/final1_trench_with_rain.json"
    # SCENARIO_CONFIG = "demo/audio_comparison/scenario_configs/final2_heli_balanced.json"
    # SCENARIO_CONFIG = "demo/audio_comparison/scenario_configs/final3_combat_softer.json"
    # SCENARIO_CONFIG = "demo/audio_comparison/scenario_configs/final5_complete_warzone.json"
    
    # 3. SNR 설정 (dB)
    # 10 dB: 중간 난이도 (추천)
    # 5 dB: 매우 어려움 (노이즈가 매우 큼)
    # 15 dB: 쉬움 (노이즈가 작음)
    TARGET_SNR_DB = 3
    
    # 4. 효과음 디렉토리 (보통 그대로)
    EFFECTS_DIR = "demo/audio_comparison/samples/sound_effects"
    
    # =============================
    
    # 실행
    batch_synthesize(
        clean_dir=CLEAN_SPEECH_DIR,
        config_file=SCENARIO_CONFIG,
        effects_dir=EFFECTS_DIR,
        output_dir=OUTPUT_DIR,
        target_snr_db=TARGET_SNR_DB
    )