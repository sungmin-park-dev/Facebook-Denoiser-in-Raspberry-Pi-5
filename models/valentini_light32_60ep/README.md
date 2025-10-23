# Valentini Light-32-Depth4 (60 Epochs)

## Performance Metrics
- **PESQ**: 2.30 (Target: 2.5, 92% achieved)
- **STOI**: 0.926 (Target: 0.85, 109% achieved) ✅
- **Model Size**: 1.7MB
- **Expected RTF**: 0.6-0.9 (Raspberry Pi 5)

## Training Details
- **Dataset**: Valentini (11,000+ clean/noisy pairs)
- **Architecture**: Light-32-Depth4
  - hidden: 32
  - depth: 4
  - resample: 2
  - glu: false
- **Epochs**: 60
- **Training Date**: 2025-10-15
- **Platform**: Google Colab GPU T4

## Usage
```python
import torch
model = torch.jit.load('models/current/best.th')
```
