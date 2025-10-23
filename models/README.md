# Models Directory

## Current Active Model
`current/` → `valentini_light32_60ep/`

## Available Models

### valentini_light32_60ep/ ⭐ (Active)
- Light-32-Depth4, Valentini 60ep
- PESQ: 2.30, STOI: 0.926
- Size: 1.7MB
- Production-ready for RP5

### debug_standard48_1ep/ (Reference)
- Standard-48-Depth5, Debug 1ep
- Size: 72MB
- Development only

## Usage
```python
from audio_pipeline.filters import AIDenoiser
denoiser = AIDenoiser()  # Auto-loads models/current/best.th
```
