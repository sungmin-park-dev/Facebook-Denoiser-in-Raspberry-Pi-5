import torchaudio
import os
from pathlib import Path

def convert_sample_files():
    print("샘플 파일 변환 시작...")
    
    # 테스트용으로 처음 10개 파일만 변환
    dirs = [
        ("dataset/valentini/train/clean", "dataset/valentini_16k/train/clean"),
        ("dataset/valentini/train/noisy", "dataset/valentini_16k/train/noisy"),
        ("dataset/valentini/test/clean", "dataset/valentini_16k/test/clean"),
        ("dataset/valentini/test/noisy", "dataset/valentini_16k/test/noisy"),
    ]
    
    for source_dir, target_dir in dirs:
        os.makedirs(target_dir, exist_ok=True)
        files = list(Path(source_dir).glob("*.wav"))[:5]  # 각 폴더당 5개만
        
        print(f"\n{source_dir} -> {target_dir}")
        for i, file in enumerate(files):
            try:
                waveform, orig_sr = torchaudio.load(file)
                print(f"  {i+1}/5: {file.name} ({orig_sr}Hz -> 16000Hz)")
                
                if orig_sr != 16000:
                    resampler = torchaudio.transforms.Resample(orig_sr, 16000)
                    resampled = resampler(waveform)
                else:
                    resampled = waveform
                
                output_path = Path(target_dir) / file.name
                torchaudio.save(str(output_path), resampled, 16000)
            except Exception as e:
                print(f"    에러: {e}")
    
    print("\n샘플 변환 완료!")

if __name__ == "__main__":
    convert_sample_files()
