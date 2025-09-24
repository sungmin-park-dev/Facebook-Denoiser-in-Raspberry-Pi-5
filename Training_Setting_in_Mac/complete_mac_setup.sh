#!/bin/bash
# 맥북 완전 설정 스크립트 (가상환경 포함)

set -e  # 에러 시 중단

echo "🍎 맥북 RPI5 Denoiser 프로젝트 완전 설정"
echo "=============================================="

# 1. 시스템 정보
echo "1. 시스템 정보 확인..."
echo "- macOS: $(sw_vers -productVersion)"
echo "- 하드웨어: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Unknown')"

# 2. 현재 디렉토리 확인
CURRENT_DIR=$(pwd)
echo "- 현재 디렉토리: $CURRENT_DIR"

# 3. 가상환경 상태 확인
echo ""
echo "2. Python 및 가상환경 확인..."
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 가상환경 활성화됨: $VIRTUAL_ENV"
    VENV_ACTIVE = true
else
    echo "⚠️ 가상환경이 활성화되지 않음"
    VENV_ACTIVE = false
fi

echo "- 시스템 Python: $(which python3)"
echo "- 현재 사용 Python: $(which python3)"

# 4. 프로젝트 존재 여부 확인
echo ""
echo "3. 프로젝트 확인..."
PROJECT_EXISTS=false

if [ -d "Facebook-Denoiser-in-Raspberry-Pi-5" ]; then
    echo "✅ 프로젝트 디렉토리 발견: Facebook-Denoiser-in-Raspberry-Pi-5"
    PROJECT_EXISTS=true
    PROJECT_DIR="$CURRENT_DIR/Facebook-Denoiser-in-Raspberry-Pi-5"
elif [ -d "denoiser" ] && [ -f "train.py" ]; then
    echo "✅ denoiser 프로젝트 발견 (현재 디렉토리)"
    PROJECT_EXISTS=true
    PROJECT_DIR="$CURRENT_DIR"
else
    echo "❌ 프로젝트를 찾을 수 없습니다"
    PROJECT_DIR=""
fi

# 5. 사용자에게 선택지 제공
echo ""
echo "4. 설정 옵션 선택:"
echo "=============================================="

if [ "$PROJECT_EXISTS" = false ]; then
    echo "프로젝트가 없습니다. 다음 중 선택하세요:"
    echo "1) 프로젝트 클론하기"
    echo "2) 기존 프로젝트 경로 입력하기"
    echo "3) 종료"
    read -p "선택 (1-3): " choice
    
    case $choice in
        1)
            echo "프로젝트 클론 중..."
            git clone https://github.com/sungmin-park-dev/Facebook-Denoiser-in-Raspberry-Pi-5.git
            PROJECT_DIR="$CURRENT_DIR/Facebook-Denoiser-in-Raspberry-Pi-5"
            PROJECT_EXISTS=true
            ;;
        2)
            read -p "프로젝트 경로를 입력하세요: " PROJECT_DIR
            if [ ! -d "$PROJECT_DIR" ]; then
                echo "❌ 유효하지 않은 경로입니다."
                exit 1
            fi
            PROJECT_EXISTS=true
            ;;
        3)
            echo "종료합니다."
            exit 0
            ;;
        *)
            echo "❌ 잘못된 선택입니다."
            exit 1
            ;;
    esac
fi

# 6. 가상환경 설정
echo ""
echo "5. 가상환경 설정:"
echo "=============================================="

VENV_DIR="$PROJECT_DIR/venv_denoiser"

if [ "$VENV_ACTIVE" = false ]; then
    if [ -d "$VENV_DIR" ]; then
        echo "✅ 기존 가상환경 발견: $VENV_DIR"
        echo "가상환경 활성화 중..."
        source "$VENV_DIR/bin/activate"
    else
        echo "새 가상환경 생성 중..."
        cd "$PROJECT_DIR"
        python3 -m venv venv_denoiser
        echo "가상환경 활성화 중..."
        source venv_denoiser/bin/activate
    fi
else
    echo "✅ 이미 가상환경이 활성화되어 있습니다"
fi

# 7. 의존성 설치
echo ""
echo "6. 의존성 확인 및 설치:"
echo "=============================================="

cd "$PROJECT_DIR"

# PyTorch 확인
echo "PyTorch 확인 중..."
if python3 -c "import torch" 2>/dev/null; then
    TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)")
    echo "✅ PyTorch 설치됨: $TORCH_VERSION"
    
    # MPS 지원 확인 (Apple Silicon)
    MPS_AVAILABLE=$(python3 -c "import torch; print(torch.backends.mps.is_available())")
    echo "- MPS 지원: $MPS_AVAILABLE"
else
    echo "❌ PyTorch 미설치, 설치 중..."
    pip install torch torchaudio
fi

# 다른 의존성 확인
echo ""
echo "기타 의존성 확인 중..."
REQUIRED_PACKAGES=(
    "hydra-core==0.11.3"
    "hydra-colorlog==0.1.4" 
    "julius"
    "numpy"
    "pystoi==0.3.3"
    "six"
    "sounddevice==0.4.0"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    package_name=$(echo $package | cut -d'=' -f1)
    if python3 -c "import $package_name" 2>/dev/null; then
        echo "✅ $package_name 설치됨"
    else
        echo "📦 $package 설치 중..."
        pip install $package
    fi
done

# PESQ는 별도 설치
if python3 -c "import pesq" 2>/dev/null; then
    echo "✅ pesq 설치됨"
else
    echo "📦 pesq 설치 중..."
    pip install git+https://github.com/ludlows/python-pesq#egg=pesq
fi

# 8. 최종 확인
echo ""
echo "7. 설치 확인:"
echo "=============================================="

echo "프로젝트 경로: $PROJECT_DIR"
echo "가상환경: $VIRTUAL_ENV"
echo "Python: $(which python3)"

# 간단한 import 테스트
echo ""
echo "모듈 import 테스트:"
python3 -c "
try:
    from denoiser.demucs import Demucs
    import torch
    print('✅ 모든 모듈 import 성공')
    print(f'✅ PyTorch: {torch.__version__}')
    if torch.backends.mps.is_available():
        print('✅ Apple Silicon MPS 사용 가능')
    elif torch.cuda.is_available():
        print('✅ NVIDIA CUDA 사용 가능')
    else:
        print('✅ CPU 사용')
except Exception as e:
    print(f'❌ Import 에러: {e}')
    exit(1
"

echo ""
echo "🎉 설정 완료!"
echo "=============================================="
echo "다음 명령어로 테스트를 시작할 수 있습니다:"
echo ""
echo "1. 가상환경 활성화 (터미널 재시작 시):"
echo "   cd $PROJECT_DIR"
echo "   source venv_denoiser/bin/activate"
echo ""
echo "2. RPI5 모델 테스트:"
echo "   python3 test_rpi5_model_on_mac.py"
echo ""
echo "3. 설정 파일 생성 후 훈련:"
echo "   python3 train.py --config-name=mac_rpi5_optimal"