#!/usr/bin/env python3
"""
전장 효과음 미리듣기 & 테스트 믹싱 (JSON 설정 기반)
- JSON 파일로 시나리오 관리
- Duration 유연 조정
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
import json
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

class SoundEffectMixer:
    def __init__(self, target_sr=16000, duration=20):
        self.target_sr = target_sr
        self.duration = duration
        self.output_length = int(duration * target_sr)
        print(f"🎧 Sound Effect Mixer")
        print(f"   Sample rate: {target_sr} Hz")
        print(f"   Duration: {duration} sec")
    
    def load_effect(self, file_path, target_length=None):
        print(f"   📂 Loading: {Path(file_path).name}")
        audio, _ = librosa.load(file_path, sr=self.target_sr, mono=True)
        
        if target_length is None:
            target_length = self.output_length
        
        if len(audio) < target_length:
            repeats = int(np.ceil(target_length / len(audio)))
            audio = np.tile(audio, repeats)[:target_length]
        else:
            audio = audio[:target_length]
        
        return audio
    
    def apply_fade(self, audio, fade_in_sec=1.0, fade_out_sec=1.0):
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
        start_sample = int(timing_sec * self.target_sr)
        
        if start_sample >= len(base_audio):
            return base_audio
        
        end_sample = min(start_sample + len(impulse_audio), len(base_audio))
        impulse_length = end_sample - start_sample
        
        base_audio[start_sample:end_sample] += impulse_audio[:impulse_length] * volume
        
        return base_audio
    
    def add_segment(self, base_audio, segment_audio, start_sec, duration_sec, 
                    volume=1.0, fade_in_sec=1.0, fade_out_sec=1.0):
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
        """JSON 설정을 목표 duration에 맞춰 스케일링 + 이벤트 자동 증식"""
        original_duration = config.get('duration', 20)
        scale_factor = target_duration / original_duration
        
        print(f"   ⚙️  Scaling: {original_duration}s → {target_duration}s (×{scale_factor:.2f})")
        
        scaled_config = config.copy()
        scaled_config['duration'] = target_duration
        scaled_config['effects'] = {}
        
        for effect_name, effect_config in config['effects'].items():
            scaled_effect = effect_config.copy()
            
            if effect_config['type'] == 'impulse':
                # 타일링: 원본 패턴 반복
                original_timings = effect_config['timings']
                num_repeats = int(np.ceil(scale_factor))
                scaled_timings = []
                
                for i in range(num_repeats):
                    offset = i * original_duration
                    for t in original_timings:
                        new_timing = t + offset
                        if new_timing < target_duration - 1:
                            scaled_timings.append(new_timing)
                
                scaled_effect['timings'] = sorted(scaled_timings)
                print(f"      {effect_name}: {len(original_timings)} → {len(scaled_timings)} events")
                
            elif effect_config['type'] == 'segment':
                # 세그먼트: 단순 스케일 (겹치면 이상함)
                scaled_effect['start'] = effect_config['start'] * scale_factor
                scaled_effect['duration'] = min(
                    effect_config['duration'] * scale_factor,
                    target_duration - scaled_effect['start'] - 1
                )
                print(f"      {effect_name}: {effect_config['start']}s → {scaled_effect['start']:.1f}s")
            
            scaled_config['effects'][effect_name] = scaled_effect
        
        return scaled_config
    
    def mix_from_config(self, config, effects_dir, output_path, override_duration=None):
        print(f"\n🎬 Mixing: {config['name']}")
        print(f"   {config['description']}")
        
        if override_duration is not None:
            config = self.scale_config_to_duration(config, override_duration)
            self.duration = override_duration
            self.output_length = int(override_duration * self.target_sr)
        
        mixed = np.zeros(self.output_length, dtype=np.float32)
        
        for effect_name, effect_config in config['effects'].items():
            print(f"\n🔊 Processing: {effect_name}")
            
            effect_path = effects_dir / effect_config['file']
            effect_type = effect_config['type']
            
            if effect_type == 'continuous':
                print(f"   Type: Continuous (vol={effect_config['volume']:.2f})")
                effect_audio = self.load_effect(effect_path)
                effect_faded = self.apply_fade(
                    effect_audio,
                    fade_in_sec=effect_config.get('fade_in', 1.0),
                    fade_out_sec=effect_config.get('fade_out', 1.0)
                )
                mixed += effect_faded * effect_config['volume']
                
            elif effect_type == 'segment':
                print(f"   Type: Segment (vol={effect_config['volume']:.2f})")
                print(f"   {effect_config['start']:.1f}s ~ {effect_config['start']+effect_config['duration']:.1f}s")
                
                effect_audio = self.load_effect(
                    effect_path,
                    target_length=int(effect_config['duration'] * self.target_sr)
                )
                
                mixed = self.add_segment(
                    mixed, effect_audio,
                    start_sec=effect_config['start'],
                    duration_sec=effect_config['duration'],
                    volume=effect_config['volume'],
                    fade_in_sec=effect_config.get('fade_in', 2.0),
                    fade_out_sec=effect_config.get('fade_out', 2.0)
                )
                
            elif effect_type == 'impulse':
                print(f"   Type: Impulse (vol={effect_config['volume']:.2f})")
                print(f"   Timings: {[f'{t:.1f}' for t in effect_config['timings']]}s")
                
                effect_audio = self.load_effect(effect_path)
                
                for timing in effect_config['timings']:
                    mixed = self.add_impulse(mixed, effect_audio, timing, effect_config['volume'])
        
        max_val = np.max(np.abs(mixed))
        if max_val > 0:
            mixed = mixed / max_val * 0.9
            print(f"\n📊 Normalized (peak: {max_val:.2f} → 0.90)")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, mixed, self.target_sr)
        
        print(f"✅ Saved: {output_path}\n")
        
        return mixed

def get_speech_duration(speech_file):
    if speech_file and Path(speech_file).exists():
        audio, sr = librosa.load(speech_file, sr=None)
        duration = len(audio) / sr
        print(f"📏 Speech duration: {duration:.2f} sec")
        return duration
    return None

def process_scenario_configs(config_dir, effects_dir, output_dir, 
                            duration=None, speech_file=None):
    config_dir = Path(config_dir)
    effects_dir = Path(effects_dir)
    output_dir = Path(output_dir)
    
    # Duration 우선순위: speech_file > duration > JSON
    target_duration = None
    
    if speech_file:
        target_duration = get_speech_duration(speech_file)
        if target_duration:
            print(f"✅ Using speech file duration: {target_duration:.2f} sec\n")
    
    if target_duration is None and duration is not None:
        target_duration = duration
        print(f"✅ Using override duration: {target_duration} sec\n")
    
    config_files = sorted(config_dir.glob('*.json'))
    
    if not config_files:
        print(f"⚠️  No JSON files in {config_dir}")
        return
    
    print("="*60)
    print("🎖️  Combat Audio Synthesis")
    print("="*60)
    print(f"Configs: {len(config_files)}")
    if target_duration:
        print(f"Duration: {target_duration} sec (scaled)")
    print("="*60)
    
    for config_file in config_files:
        print("\n" + "="*60)
        print(f"📋 {config_file.name}")
        print("="*60)
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            final_duration = target_duration if target_duration else config.get('duration', 20)
            
            mixer = SoundEffectMixer(target_sr=16000, duration=final_duration)
            
            output_filename = f"{config['name']}.wav"
            if target_duration and target_duration != config.get('duration', 20):
                output_filename = f"{config['name']}_{int(final_duration)}s.wav"
            
            output_path = output_dir / output_filename
            
            mixer.mix_from_config(config, effects_dir, output_path, 
                                 override_duration=target_duration)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("🎉 Complete!")
    print("="*60)
    print(f"\n📂 Output: {output_dir}")
    if target_duration:
        print(f"⏱️  Duration: {target_duration:.2f} sec")

# ==================== 메인 ====================
if __name__ == "__main__":
    
    # ===== 여기만 수정하세요! =====
    
    # 옵션 1: JSON 기본 duration 사용 (보통 20초)
    DURATION = 60     # None 으로 설정, 고정 길이 원할 시 초 단위 숫자 입력
    
    # 옵션 2: 음성 파일 길이에 자동 맞춤 (최우선)
    SPEECH_FILE = None
    # SPEECH_FILE = "demo/audio_comparison/samples/clean_speech/my_voice.wav"
    
    # =============================
    
    # 경로 설정 (보통 그대로)
    CONFIG_DIR = "demo/audio_comparison/scenario_configs"
    EFFECTS_DIR = "demo/audio_comparison/samples/sound_effects"
    OUTPUT_DIR = "demo/audio_comparison/samples/final_combat"
    
    # 실행
    process_scenario_configs(
        config_dir=CONFIG_DIR,
        effects_dir=EFFECTS_DIR,
        output_dir=OUTPUT_DIR,
        duration=DURATION,
        speech_file=SPEECH_FILE
    )