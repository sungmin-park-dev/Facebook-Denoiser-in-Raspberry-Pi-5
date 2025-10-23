# Models Directory

This directory contains the trained denoiser models used by the audio pipeline.

## Available Models

### best.th
- **Model**: Light-32-Depth4 architecture
- **Source**: `outputs/exp_batch_size=4,dset=debug,epochs=1/best.th`
- **Training**: Debug dataset, 1 epoch, batch size 4
- **Performance**: Optimized for real-time processing on Raspberry Pi 5
- **Usage**: Default model for the audio pipeline

## Model Loading

The audio pipeline automatically detects and loads the model from this directory:

```python
from audio_pipeline.filters import AIDenoiser

# Auto-detects models/best.th
denoiser = AIDenoiser()
```

## Alternative Models

If you have other trained models, place them in this directory and specify the path:

```python
denoiser = AIDenoiser(model_path="models/your_model.th")
```

## Model Training

For training new models, refer to the original training scripts in the `archive/training_mac/` directory or the main `train.py` script.