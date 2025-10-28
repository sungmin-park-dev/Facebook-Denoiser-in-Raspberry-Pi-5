#!/usr/bin/env python3
"""
Facebook Denoiser 모델 통합 다운로드 스크립트
- dns64, dns48, master64 한번에 다운로드
"""

import torch
import os
from pathlib import Path

# 프로젝트 루트 및 models 폴더 설정
ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "models"

def download_model(model_name, loader_func):
    """개별 모델 다운로드"""
    model_path = MODELS_DIR / f"{model_name}.th"
    
    # 이미 존재하면 스킵
    if model_path.exists():
        size_mb = os.path.getsize(model_path) / (1024**2)
        print(f"⏭️  {model_name}.th already exists ({size_mb:.2f} MB)")
        return
    
    # 다운로드
    print(f"📥 Downloading {model_name} model...")
    model = loader_func()
    
    # 저장
    torch.save(model.state_dict(), model_path)
    size_mb = os.path.getsize(model_path) / (1024**2)
    print(f"✅ {model_name}.th saved ({size_mb:.2f} MB)\n")

def main():
    print("="*60)
    print("🤖 Facebook Denoiser Model Downloader")
    print("="*60)
    print(f"📂 Target directory: {MODELS_DIR}\n")
    
    # models 폴더 생성
    MODELS_DIR.mkdir(exist_ok=True)
    
    # 다운로드할 모델 목록
    models_to_download = {
        "dns64": lambda: torch.hub.load('facebookresearch/denoiser', 'dns64', force_reload=True),
        "dns48": lambda: torch.hub.load('facebookresearch/denoiser', 'dns48', force_reload=True),
        "master64": lambda: torch.hub.load('facebookresearch/denoiser', 'master64', force_reload=True)
    }
    
    # 순차 다운로드
    for model_name, loader_func in models_to_download.items():
        try:
            download_model(model_name, loader_func)
        except Exception as e:
            print(f"❌ Error downloading {model_name}: {e}\n")
    
    # 최종 요약
    print("="*60)
    print("📊 Download Summary:")
    print("="*60)
    
    for model_name in models_to_download.keys():
        model_path = MODELS_DIR / f"{model_name}.th"
        if model_path.exists():
            size_mb = os.path.getsize(model_path) / (1024**2)
            print(f"✅ {model_name}.th - {size_mb:.2f} MB")
        else:
            print(f"❌ {model_name}.th - NOT FOUND")
    
    print("="*60)
    print("🎉 Download complete!")
    print("\n💡 Usage: python demo/mac_realtime.py")

if __name__ == "__main__":
    main()