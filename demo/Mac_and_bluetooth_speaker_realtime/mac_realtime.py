#!/usr/bin/env python3
"""
Mac 실시간 음성 디노이징 데모
- Facebook 사전훈련 모델 선택 가능
- Enter로 디노이징 ON/OFF 토글
- 'q' + Enter로 종료
- 블루투스 스피커 자동 탐색
"""

import torch
import pyaudio
import numpy as np
import threading
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가 (demo/Mac_and_bluetooth_speaker_realtime/ → 프로젝트 루트)

ROOT = Path(__file__).parent.parent.parent  
sys.path.insert(0, str(ROOT))

from denoiser import pretrained
from denoiser.demucs import DemucsStreamer

from denoiser import pretrained
from denoiser.demucs import DemucsStreamer

# ==================== 설정 ====================
SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # 32ms @ 16kHz

# 사용 가능한 모델 목록
AVAILABLE_MODELS = {
    "1": {
        # Facebook DNS Challenge 최고 사양 모델
        # - 파라미터: hidden=64, depth=5
        # - 용량: ~128MB
        # - 성능: 최고 품질, Mac에서 RTF < 0.1
        "name": "dns64",
        "path": ROOT / "models" / "dns64.th",
        "description": "Facebook DNS64 (hidden=64, depth=5) - 최고 사양",
        "loader": lambda: pretrained.dns64()
    },
    "2": {
        # Facebook DNS Challenge 고사양 모델
        # - 파라미터: hidden=48, depth=5
        # - 용량: ~75MB
        # - 성능: dns64보다 약간 낮지만 빠름
        "name": "dns48",
        "path": ROOT / "models" / "dns48.th",
        "description": "Facebook DNS48 (hidden=48, depth=5) - 고사양",
        "loader": lambda: pretrained.dns48()
    },
    "3": {
        # Valentini 데이터셋 사전훈련 모델
        # - 파라미터: hidden=64, depth=5
        # - 용량: ~128MB
        # - 특징: clean speech 데이터로 훈련
        "name": "master64",
        "path": ROOT / "models" / "master64.th",
        "description": "Facebook Master64 (hidden=64, depth=5) - Valentini 사전훈련",
        "loader": lambda: pretrained.master64()
    },
    "4": {
        # RP5 최적화 커스텀 모델 (직접 훈련)
        # - 파라미터: hidden=32, depth=4, resample=2
        # - 용량: ~2MB
        # - 성능: RP5에서 RTF=0.834
        # - 특징: 실시간 처리 최적화
        "name": "valentini_light32",
        "path": ROOT / "models" / "valentini_light32_60ep" / "best.th",
        "description": "Custom Light32 (hidden=32, depth=4) - RP5 최적화",
        "loader": None  # 커스텀 체크포인트는 직접 로드
    }
}

class RealtimeDenoiser:
    def __init__(self):
        self.denoising_enabled = True
        self.running = True
        
        # PyAudio 초기화
        self.p = pyaudio.PyAudio()
        
        # 모델 선택 및 로드
        self.model_info = self._select_model()
        print(f"🔄 Loading {self.model_info['name']} model...")
        self.model = self._load_model(self.model_info)
        self.model.eval()
        self.streamer = DemucsStreamer(self.model, dry=0, num_frames=1)
        print("✅ Model loaded")
        
        # 디바이스 선택
        self.input_device, self.output_device = self._select_devices()
    
    def _select_model(self):
        """모델 선택"""
        print("\n" + "="*50)
    
        print("🤖 Available Models:")
        print("="*50)
        
        for key, info in AVAILABLE_MODELS.items():
            status = "✅" if info['path'].exists() else "❌"
            print(f"[{key}] {status} {info['description']}")
        
        print("="*50)
        print("💡 Tip: Run 'python demo/download_models.py' to download missing models")
        print("="*50)
        
        while True:
            choice = input("Select model number: ").strip()
            if choice in AVAILABLE_MODELS:
                model_info = AVAILABLE_MODELS[choice]
                
                # 모델 파일 존재 확인
                if not model_info['path'].exists():
                    print(f"⚠️  Model file not found: {model_info['path']}")
                    print("   Please download or train this model first.\n")
                    continue
                
                return model_info
            else:
                print("❌ Invalid choice. Please try again.\n")
    
    def _load_model(self, model_info):
        """모델 로드"""
        if model_info['loader'] is not None:
            # Facebook 사전훈련 모델 (torch.hub 사용)
            return model_info['loader']().cpu()
        else:
            # 커스텀 훈련 모델 (체크포인트 직접 로드)
            from denoiser.demucs import Demucs
            
            # 체크포인트 로드
            checkpoint = torch.load(model_info['path'], map_location='cpu')
            
            # 모델 구조 재구성 (Light32 파라미터)
            model = Demucs(
                hidden=32,
                depth=4,
                resample=2,
                kernel_size=8,
                stride=4,
                growth=1.5,
                glu=False
            )
            
            # 가중치 로드
            if 'state' in checkpoint:
                model.load_state_dict(checkpoint['state'])
            else:
                model.load_state_dict(checkpoint)
            
            return model.cpu()
        
    def _select_devices(self):
        """오디오 입출력 디바이스 선택"""
        print("\n" + "="*50)
        print("🎤 Available Input Devices:")
        print("="*50)
        
        input_devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info['name']))
                print(f"[{i}] {info['name']}")
        
        print("\n" + "="*50)
        print("🔊 Available Output Devices:")
        print("="*50)
        
        output_devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                output_devices.append((i, info['name']))
                print(f"[{i}] {info['name']}")
                # 블루투스 스피커 자동 감지
                if 'bluetooth' in info['name'].lower():
                    print(f"  └─ 🔵 Bluetooth device detected!")
        
        # 사용자 선택
        print("\n" + "="*50)
        input_idx = int(input("Select INPUT device number: "))
        output_idx = int(input("Select OUTPUT device number: "))
        
        return input_idx, output_idx
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """실시간 오디오 처리 콜백"""
        if not self.running:
            return (in_data, pyaudio.paComplete)
        
        # NumPy 변환
        audio_np = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        if self.denoising_enabled:
            # 디노이징 처리
            with torch.no_grad():
                audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)  # [1, samples]
                enhanced = self.streamer.feed(audio_tensor)
                
                if enhanced is not None:
                    audio_np = enhanced.squeeze(0).numpy()
        
        # 출력 변환
        out_data = (audio_np * 32768.0).astype(np.int16).tobytes()
        
        return (out_data, pyaudio.paContinue)
    
    def _toggle_listener(self):
        """Enter로 토글, 'q' + Enter로 종료"""
        print("\n" + "="*50)
        print("🎛️  Controls:")
        print("="*50)
        print("  Enter       : Toggle denoising ON/OFF")
        print("  'q' + Enter : Quit")
        print("="*50)
        
        while self.running:
            cmd = input().strip().lower()
            
            if cmd == 'q':
                print("\n👋 Shutting down...")
                self.running = False
                break
            else:
                # Enter만 눌렀거나 다른 입력 시 토글
                self.denoising_enabled = not self.denoising_enabled
                status = "🟢 ON" if self.denoising_enabled else "🔴 OFF"
                print(f"\n[TOGGLE] Denoising: {status}\n")
    
    def run(self):
        """실시간 처리 시작"""
        # 입력 스트림
        stream_in = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.input_device,
            frames_per_buffer=CHUNK_SIZE
        )
        
        # 출력 스트림
        stream_out = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            output_device_index=self.output_device,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=None  # 수동 모드
        )
        
        # 토글 리스너 스레드
        toggle_thread = threading.Thread(target=self._toggle_listener, daemon=True)
        toggle_thread.start()
        
        print("\n🎙️  Recording started... (Press Enter to toggle)\n")
        
        try:
            while self.running:
                # 입력 읽기
                in_data = stream_in.read(CHUNK_SIZE, exception_on_overflow=False)
                
                # 처리
                out_data, _ = self._audio_callback(in_data, CHUNK_SIZE, None, None)
                
                # 출력
                stream_out.write(out_data)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        
        finally:
            stream_in.stop_stream()
            stream_in.close()
            stream_out.stop_stream()
            stream_out.close()
            self.p.terminate()
            print("✅ Cleanup complete")

# ==================== 메인 ====================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🎵 Mac Realtime Denoising Demo")
    print("="*50)
    
    denoiser = RealtimeDenoiser()
    denoiser.run()