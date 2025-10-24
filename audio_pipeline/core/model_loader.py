"""
AI Model Loader

Handles loading and managing denoiser models for real-time audio processing.
Supports local checkpoints and pretrained models.
"""

import torch
from pathlib import Path
from typing import Union, Optional
import warnings


class ModelLoader:
    """Load and manage AI denoiser models"""
    
    # Model registry
    MODELS = {
        'Light-32-Depth4': {
            'path': 'models/current/best.th',
            'description': 'Optimized for RP5 (RTF 0.092)',
            'params': '434K',
            'size': '1.7MB'
        },
        'dns48': {
            'pretrained': 'dns48',
            'description': 'Facebook pretrained DNS 48',
            'params': '18.87M',
            'size': '~72MB'
        },
        'dns64': {
            'pretrained': 'dns64',
            'description': 'Facebook pretrained DNS 64',
            'params': '33.53M',
            'size': '~128MB'
        }
    }
    
    @classmethod
    def load(cls, model_name: str = 'Light-32-Depth4', device: str = 'cpu') -> torch.nn.Module:
        """
        Load a denoiser model
        
        Args:
            model_name: Model identifier ('Light-32-Depth4', 'dns48', 'dns64')
            device: Device to load model on ('cpu' or 'cuda')
        
        Returns:
            Loaded PyTorch model in eval mode
        
        Examples:
            >>> model = ModelLoader.load('Light-32-Depth4')
            >>> model = ModelLoader.load('dns48', device='cuda')
        """
        if model_name not in cls.MODELS:
            available = ', '.join(cls.MODELS.keys())
            raise ValueError(f"Unknown model '{model_name}'. Available: {available}")
        
        model_info = cls.MODELS[model_name]
        
        # Load from local checkpoint
        if 'path' in model_info:
            model_path = Path(model_info['path'])
            if model_path.exists():
                print(f"📂 Loading {model_name} from {model_path}")
                model = cls._load_checkpoint(model_path, device)
            else:
                # Fallback: try alternative paths
                alt_paths = [
                    Path('models') / 'best.th',
                    Path('models') / 'current' / 'best.th',
                    Path('..') / 'models' / 'current' / 'best.th'
                ]
                
                for alt_path in alt_paths:
                    if alt_path.exists():
                        print(f"📂 Loading {model_name} from {alt_path}")
                        model = cls._load_checkpoint(alt_path, device)
                        break
                else:
                    raise FileNotFoundError(
                        f"Model checkpoint not found at {model_path} or alternative paths"
                    )
        
        # Load pretrained model
        elif 'pretrained' in model_info:
            print(f"🌐 Loading pretrained model: {model_info['pretrained']}")
            model = cls._load_pretrained(model_info['pretrained'], device)
        
        else:
            raise ValueError(f"Invalid model configuration for {model_name}")
        
        # Set to eval mode
        model.eval()
        model.to(device)
        
        print(f"✅ Model loaded: {model_name}")
        print(f"   Description: {model_info['description']}")
        print(f"   Parameters: {model_info['params']}")
        print(f"   Device: {device}")
        
        return model
    
    @staticmethod
    def _load_checkpoint(path: Path, device: str) -> torch.nn.Module:
        """Load model from checkpoint file"""
        try:
            pkg = torch.load(path, map_location=device, weights_only=False)
            
            # Handle different checkpoint formats
            if isinstance(pkg, dict):
                if 'model' in pkg:
                    # Direct model in checkpoint
                    model = pkg['model']
                elif 'state' in pkg and 'class' in pkg:
                    # Denoiser format: class + args + kwargs + state
                    from denoiser.demucs import Demucs
                    klass = pkg['class']
                    args = pkg.get('args', [])
                    kwargs = pkg.get('kwargs', {})
                    state = pkg['state']
                    
                    # Reconstruct model
                    model = klass(*args, **kwargs)
                    model.load_state_dict(state)
                elif 'state_dict' in pkg:
                    # Need to reconstruct model architecture
                    from denoiser.demucs import Demucs
                    model = Demucs(**pkg.get('args', {}))
                    model.load_state_dict(pkg['state_dict'])
                else:
                    raise ValueError("Unknown checkpoint format")
            else:
                # Direct model save
                model = pkg
            
            return model
        
        except Exception as e:
            raise RuntimeError(f"Failed to load checkpoint from {path}: {e}")
    
    @staticmethod
    def _load_pretrained(model_name: str, device: str) -> torch.nn.Module:
        """Load pretrained model from denoiser library"""
        try:
            from denoiser import pretrained
            
            # Map model names to pretrained functions
            pretrained_models = {
                'dns48': pretrained.dns48,
                'dns64': pretrained.dns64,
                'master64': pretrained.master64
            }
            
            if model_name not in pretrained_models:
                raise ValueError(f"Unknown pretrained model: {model_name}")
            
            model = pretrained_models[model_name]()
            return model
        
        except ImportError:
            raise ImportError(
                "denoiser library not found. Install with: pip install denoiser"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load pretrained model {model_name}: {e}")
    
    @classmethod
    def list_models(cls) -> None:
        """Print available models"""
        print("\n" + "="*60)
        print("📚 Available Models:")
        print("="*60)
        for name, info in cls.MODELS.items():
            print(f"\n🔹 {name}")
            print(f"   Description: {info['description']}")
            print(f"   Parameters: {info['params']}")
            print(f"   Size: {info['size']}")
            if 'path' in info:
                path = Path(info['path'])
                status = "✅ Available" if path.exists() else "❌ Not found"
                print(f"   Status: {status}")
        print("="*60 + "\n")
    
    @staticmethod
    def get_model_info(model: torch.nn.Module) -> dict:
        """Get model information"""
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        return {
            'total_params': total_params,
            'trainable_params': trainable_params,
            'model_size_mb': total_params * 4 / 1024 / 1024  # float32
        }


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Loader Utility")
    parser.add_argument('--list', action='store_true', help='List available models')
    parser.add_argument('--load', type=str, help='Load and test a model')
    parser.add_argument('--device', type=str, default='cpu', help='Device (cpu/cuda)')
    
    args = parser.parse_args()
    
    if args.list:
        ModelLoader.list_models()
    
    elif args.load:
        model = ModelLoader.load(args.load, device=args.device)
        info = ModelLoader.get_model_info(model)
        
        print("\n📊 Model Statistics:")
        print(f"   Total parameters: {info['total_params']:,}")
        print(f"   Trainable parameters: {info['trainable_params']:,}")
        print(f"   Model size: {info['model_size_mb']:.2f} MB")
        
        # Test inference
        print("\n🧪 Testing inference...")
        dummy_input = torch.randn(1, 1, 16000)  # 1 second @ 16kHz
        with torch.no_grad():
            output = model(dummy_input)
        print(f"✅ Input shape: {dummy_input.shape}")
        print(f"✅ Output shape: {output.shape}")
    
    else:
        parser.print_help()