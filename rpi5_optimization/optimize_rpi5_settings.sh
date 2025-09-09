#!/bin/bash
# 라즈베리파이 5 최적화 설정 스크립트

echo "라즈베리파이 5 실시간 음성 디노이징 최적화 설정"
echo "================================================"

# 1. CPU 거버너를 performance로 설정
echo "1. CPU 성능 최적화..."
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 2. CPU 주파수 확인
echo "2. 현재 CPU 주파수:"
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# 3. 메모리 최적화 설정
echo "3. 메모리 최적화..."
# GPU 메모리 할당 최소화 (헤드리스 환경에서)
# /boot/config.txt에 gpu_mem=16 추가 권장

# 4. 스왑 사용 최소화
echo "4. 스왑 설정 확인..."
cat /proc/swaps
echo "현재 swappiness:"
cat /proc/sys/vm/swappiness

# 5. PyTorch 최적화 환경변수 설정
echo "5. PyTorch 최적화 환경변수 설정..."
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4
export VECLIB_MAXIMUM_THREADS=4

# 6. 시스템 정보 출력
echo "6. 시스템 정보:"
echo "CPU 정보:"
lscpu | grep -E "(Model name|CPU\(s\)|Thread|MHz)"
echo ""
echo "메모리 정보:"
free -h
echo ""
echo "온도 확인:"
vcgencmd measure_temp

echo ""
echo "최적화 설정 완료!"
echo "RTF 테스트를 실행하려면: python3 rtf_test_models.py"
