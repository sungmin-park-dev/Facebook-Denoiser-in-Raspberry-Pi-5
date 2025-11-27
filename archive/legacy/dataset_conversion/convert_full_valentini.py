import torchaudio
import os
from pathlib import Path
import sys

def convert_full_valentini():
    print("전체 Valentini 데이터 변환 시작...")
    
    dirs = [
        ("dataset/valentini/train/clean", "dataset/valentini_16k_full/train/clean"),
        ("dataset/valentini/train/noisy", "dataset/valentini_16k_full/train/noisy"),
        ("dataset/valentini/test/clean", "dataset/valentini_16k_full/test/clean"),
        ("dataset/valentini/test/noisy", "dataset/valentini_16k_full/test/noisy"),
    ]
    
    total_files = 0
    for source_dir, target_dir in dirs:
        files = list(Path(source_dir).glob("*.wav"))
        total_files += len(files)
    
    print(f"총 {total_files}개 파일 변환 예정")
    converted = 0
    
    for source_dir, target_dir in dirs:
        os.makedirs(target_dir, exist_ok=True)
        files = list(Path(source_dir).glob("*.wav"))
        
        print(f"\n{source_dir} -> {target_dir} ({len(files)}개 파일)")
        
        for i, file in enumerate(files):
            try:
                waveform, orig_sr = torchaudio.load(file)
                
                if orig_sr != 16000:
                    resampler = torchaudio.transforms.Resample(orig_sr, 16000)
                    resampled = resampler(waveform)
                else:
                    resampled = waveform
                
                output_path = Path(target_dir) / file.name
                torchaudio.save(str(output_path), resampled, 16000)
                
                converted += 1
                if converted % 100 == 0:
                    progress = (converted / total_files) * 100
                    print(f"  진행률: {converted}/{total_files} ({progress:.1f}%)")
                    
            except Exception as e:
                print(f"    에러 {file.name}: {e}")
    
    print(f"\n전체 변환 완료: {converted}/{total_files}개")

if __name__ == "__main__":
    convert_full_valentini()
