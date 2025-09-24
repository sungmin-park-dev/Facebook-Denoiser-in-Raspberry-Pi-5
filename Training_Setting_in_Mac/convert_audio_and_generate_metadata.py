#!/usr/bin/env python3
"""
Multi-Environment Audio Converter for Denoiser Training
Supports both Mac and Google Colab environments

Author: Sung-Min, Park  
Date: Sep 23, 2024
Description: 
- Auto-detect environment (Mac/Colab)
- Convert audio files to 16kHz
- Generate JSON metadata files for denoiser training
- Google Drive integration for Colab
- Enhanced data validation and copying
"""

import os
import json
import shutil
import platform
import sys
import numpy as np
import torch
import torchaudio
from pathlib import Path
from tqdm import tqdm
import argparse
import time


# ===================================================================
# CONFIGURATION
# ===================================================================

class Config:
    """Configuration class for different environments"""
    
    # Google Colab default paths
    COLAB_PATHS = {
        'original': "/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/original_dataset",
        'converted': "/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/converted_data", 
        'denoiser': "/content/denoiser/dataset/valentini/",
        'egs': "/content/denoiser/egs/valentini",
        'config': "/content/denoiser/conf/dset/valentini.yaml"
    }
    
    # Mac default paths  
    MAC_PATHS = {
        'original': "./dataset/valentini_original",
        'converted': "./dataset/valentini_converted", 
        'denoiser': "./dataset/valentini/",
        'egs': "./egs/valentini",
        'config': "./conf/dset/valentini.yaml"
    }
    
    # Valentini dataset folder structure
    VALENTINI_FOLDERS = {
        "train_clean_28spk_wav": "train/clean",
        "train_noisy_28spk_wav": "train/noisy", 
        "test_clean_wav": "test/clean",
        "test_noisy_wav": "test/noisy"
    }
    
    TARGET_SAMPLE_RATE = 16000


# ===================================================================
# ENVIRONMENT DETECTION
# ===================================================================

class EnvironmentDetector:
    """Detect and setup environment (Colab vs Local)"""
    
    @staticmethod
    def detect_environment():
        """Auto-detect current environment"""
        try:
            # Check if running in Google Colab
            import google.colab
            return 'colab'
        except ImportError:
            pass
        
        # Check operating system
        if platform.system() == 'Darwin':
            return 'mac'
        elif platform.system() == 'Linux':
            return 'linux'
        else:
            return 'windows'
    
    @staticmethod
    def setup_google_drive():
        """Mount Google Drive in Colab environment"""
        try:
            from google.colab import drive
            drive.mount('/content/drive')
            print("✅ Google Drive mounted successfully")
            return True
        except ImportError:
            print("⚠️ Not in Colab environment, skipping Drive mount")
            return False
        except Exception as e:
            print(f"❌ Failed to mount Google Drive: {e}")
            return False


# ===================================================================
# DATA VALIDATION
# ===================================================================

class DataValidator:
    """Enhanced data validation and checking"""
    
    def __init__(self, target_sample_rate=16000):
        self.target_sample_rate = target_sample_rate
    
    def check_16khz_format(self, file_path):
        """Check if file is 16kHz format"""
        try:
            info = torchaudio.info(file_path)
            if info.sample_rate != self.target_sample_rate:
                print(f">>> ❌ {file_path.name} - sample rate: {info.sample_rate}Hz")
                return False
            return True
        except Exception as e:
            print(f">>> ❌ Reading Error - {file_path.name}: {e}")
            return False
    
    def check_converted_data(self, converted_path, check_sample=None):
        """Check if converted data exists and is valid"""
        print(f"🔍 Checking converted data at: {converted_path}")
        
        if not Path(converted_path).exists():
            print("❌ Converted data directory does not exist")
            return False
        
        print(f"📁 Path exists: {converted_path}")
        
        total_errors = 0
        all_folders_exist = True
        
        for split in ['train', 'test']:
            for type_ in ['clean', 'noisy']:
                path = Path(converted_path) / split / type_
                
                if not path.exists():
                    print(f">>> ❌ {split}/{type_} folder missing")
                    all_folders_exist = False
                    continue
                
                wav_files = list(path.glob("*.wav"))
                count = len(wav_files)
                error_count = 0
                
                if count > 0:
                    print(f">>> 📋 {split}/{type_}: Checking files...")
                    
                    if check_sample in ("All", "all"):
                        sample_files = wav_files
                    else:
                        sample_size = min(5, count)
                        sample_indices = np.random.choice(count, size=sample_size, replace=False)
                        sample_files = [wav_files[i] for i in sample_indices]
                    
                    for sample_file in sample_files:
                        if not self.check_16khz_format(sample_file):
                            error_count += 1
                    
                    total_errors += error_count
                    print(f">>> ✅ {split}/{type_}: Total {count}, Valid 16kHz {count - error_count}")
                    
                    if error_count > 0:
                        print(f">>> ❌ {split}/{type_}: {error_count} files with errors")
                else:
                    print(f">>> ⚠️ {split}/{type_}: No files found")
                    all_folders_exist = False
        
        if not all_folders_exist:
            print("❌ Incomplete folder structure")
            return False
        
        if total_errors > 0:
            print(f"❌ Total {total_errors} files are not 16kHz")
            return False
        
        print("✅ All validation passed! 16kHz data ready")
        return True
    
    def validate_source_structure(self, source_path):
        """Validate original dataset structure"""
        print(f"🔍 Validating source structure: {source_path}")
        
        source_path = Path(source_path)
        if not source_path.exists():
            print(f"❌ Source path does not exist: {source_path}")
            return False
        
        required_folders = Config.VALENTINI_FOLDERS.keys()
        missing_folders = []
        
        for folder in required_folders:
            folder_path = source_path / folder
            if not folder_path.exists():
                missing_folders.append(folder)
            else:
                wav_count = len(list(folder_path.glob("*.wav")))
                print(f">>> ✅ {folder}: {wav_count} files")
        
        if missing_folders:
            print(f"❌ Missing folders: {missing_folders}")
            return False
        
        print("✅ Source structure validation passed")
        return True


# ===================================================================
# FILE MANAGEMENT
# ===================================================================

class FileManager:
    """File operations and management"""
    
    @staticmethod
    def copy_to_denoiser(source_path, target_path):
        """Copy converted data to denoiser dataset path"""
        print(f"\n📋 Copying to denoiser path: {target_path}")
        
        try:
            # Remove existing directory if exists
            if Path(target_path).exists():
                shutil.rmtree(target_path)
            
            # Create target directory
            os.makedirs(target_path, exist_ok=True)
            
            # Copy all subdirectories
            for item in Path(source_path).iterdir():
                if item.is_dir():
                    shutil.copytree(item, Path(target_path) / item.name)
                    print(f">>> ✅ Copied {item.name}")
            
            print("✅ Copy to denoiser completed!")
            return True
            
        except Exception as e:
            print(f"❌ Copy error: {e}")
            return False
    
    @staticmethod
    def create_directories(paths):
        """Create necessary directories"""
        for path_name, path_value in paths.items():
            os.makedirs(Path(path_value).parent if path_name == 'config' else path_value, exist_ok=True)


# ===================================================================
# MAIN CONVERTER CLASS
# ===================================================================

class MultiEnvironmentAudioConverter:
    """Multi-environment audio converter with enhanced features"""
    
    def __init__(self, custom_paths=None):
        self.env = EnvironmentDetector.detect_environment()
        self.config = Config()
        self.validator = DataValidator(Config.TARGET_SAMPLE_RATE)
        self.file_manager = FileManager()
        
        # Setup environment-specific paths
        self.paths = self._setup_paths(custom_paths)
        
        # Setup environment
        self._setup_environment()
        
        print(f"🔧 Environment: {self.env.upper()}")
        print(f"🎯 Target sample rate: {Config.TARGET_SAMPLE_RATE}Hz")
    
    def _setup_paths(self, custom_paths):
        """Setup paths based on environment and custom overrides"""
        if custom_paths:
            return custom_paths
        elif self.env == 'colab':
            return Config.COLAB_PATHS.copy()
        else:
            return Config.MAC_PATHS.copy()
    
    def _setup_environment(self):
        """Setup environment-specific configurations"""
        print("🔧 Environment Setup")
        print("=" * 50)
        
        print(f"PyTorch: {torch.__version__}")
        print(f"Torchaudio: {torchaudio.__version__}")
        
        # Setup device
        if torch.backends.mps.is_available():
            print("✅ Apple Silicon MPS available")
            self.device = "mps"
        elif torch.cuda.is_available():
            print("✅ NVIDIA CUDA available")
            self.device = "cuda"
        else:
            print("⚠️ Using CPU only")
            self.device = "cpu"
        
        print(f"Using device: {self.device}")
        
        # Setup Google Drive for Colab
        if self.env == 'colab':
            EnvironmentDetector.setup_google_drive()
    
    def resample_and_save(self, source_file, target_dir):
        """Resample audio file to target sample rate and save"""
        try:
            # Load audio
            waveform, orig_sr = torchaudio.load(source_file)
            
            # Resample if needed
            if orig_sr != Config.TARGET_SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(orig_sr, Config.TARGET_SAMPLE_RATE)
                resampled = resampler(waveform)
            else:
                resampled = waveform
            
            # Save to target directory
            output_path = target_dir / source_file.name
            torchaudio.save(str(output_path), resampled, Config.TARGET_SAMPLE_RATE)
            
            return True
            
        except Exception as e:
            print(f"❌ Resampling Error {source_file.name}: {e}")
            return False
    
    def convert_valentini_dataset(self, source_path=None, target_path=None):
        """Convert Valentini dataset to 16kHz"""
        source_path = source_path or self.paths['original']
        target_path = target_path or self.paths['converted']
        
        print("🔄 Starting Valentini dataset conversion...")
        print(f"📁 Source: {source_path}")
        print(f"📁 Target: {target_path}")
        
        # Validate source structure
        if not self.validator.validate_source_structure(source_path):
            return False
        
        # Create target directory
        os.makedirs(target_path, exist_ok=True)
        
        total_converted = 0
        total_errors = 0
        
        for source_folder, target_folder in Config.VALENTINI_FOLDERS.items():
            source_dir = Path(source_path) / source_folder
            target_dir = Path(target_path) / target_folder
            
            if not source_dir.exists():
                print(f"⚠️ {source_dir} folder not found. Skipping.")
                continue
            
            os.makedirs(target_dir, exist_ok=True)
            
            # Get source files
            source_files = list(source_dir.glob("*.wav"))
            print(f"📂 {source_folder}: {len(source_files)} files")
            
            converted = 0
            errors = 0
            
            for file in tqdm(source_files, 
                           desc=f"🔄 {source_folder}", 
                           unit="files", leave=True):
                
                if self.resample_and_save(file, target_dir):
                    converted += 1
                else:
                    errors += 1
            
            print(f"✅ {source_folder}: {converted} success, {errors} failed")
            total_converted += converted
            total_errors += errors
        
        if total_converted > 0:
            print(f"\n💾 Conversion completed! ({total_converted} files)")
            return True
        else:
            print("❌ No files converted")
            return False
    
    def generate_audio_metadata(self, audio_dir):
        """Generate JSON metadata for audio directory"""
        audio_files = []
        
        for wav_file in Path(audio_dir).glob("*.wav"):
            try:
                info = torchaudio.info(wav_file)
                # Format: [file_path, length_in_samples]
                audio_files.append([str(wav_file), info.num_frames])
            except Exception as e:
                print(f"❌ Error processing {wav_file}: {e}")
        
        return audio_files
    
    def generate_metadata_files(self, dataset_path=None, egs_path=None):
        """Generate JSON metadata files for denoiser training"""
        dataset_path = dataset_path or self.paths['denoiser']
        egs_path = egs_path or self.paths['egs']
        
        print("📋 Generating JSON metadata files...")
        
        # Create egs directory structure
        train_dir = Path(egs_path) / "tr"
        test_dir = Path(egs_path) / "tt"
        os.makedirs(train_dir, exist_ok=True)
        os.makedirs(test_dir, exist_ok=True)
        
        # Generate metadata for each split and type
        metadata_files = [
            ("train/clean", train_dir / "clean.json"),
            ("train/noisy", train_dir / "noisy.json"),
            ("test/clean", test_dir / "clean.json"),
            ("test/noisy", test_dir / "noisy.json")
        ]
        
        for data_dir, json_file in metadata_files:
            audio_dir = Path(dataset_path) / data_dir
            
            if audio_dir.exists():
                print(f">>> Generating {json_file}...")
                metadata = self.generate_audio_metadata(audio_dir)
                
                with open(json_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                print(f">>> ✅ {json_file}: {len(metadata)} files")
            else:
                print(f">>> ❌ {audio_dir} not found")
        
        print("✅ JSON metadata generation completed!")
    
    def create_dataset_config(self, config_path=None, egs_path=None):
        """Create dataset configuration file"""
        config_path = config_path or self.paths['config']
        egs_path = egs_path or self.paths['egs']
        
        config_content = f"""# Valentini dataset configuration
dset:
  train: {egs_path}/tr
  valid:
  test: {egs_path}/tt
  noisy_json: {egs_path}/tt/noisy.json
  noisy_dir:
  matching: sort
eval_every: 10
pesq: 1
"""
        
        os.makedirs(Path(config_path).parent, exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        print(f"✅ Dataset configuration saved to: {config_path}")
    
    def run_full_pipeline(self, check_only=False):
        """Run the complete conversion and setup pipeline"""
        print("🚀 Starting Full Pipeline")
        print("=" * 60)
        
        if check_only:
            # Only check existing converted data
            print("🔍 Checking existing converted data...")
            if self.validator.check_converted_data(self.paths['converted'], check_sample="all"):
                print("⚡ Using existing converted data!")
                success = True
            else:
                print("❌ Converted data validation failed")
                return False
        else:
            # Check if converted data exists and is valid
            if self.validator.check_converted_data(self.paths['converted'], check_sample=5):
                print("⚡ Using existing converted data!")
                success = True
            else:
                print("🔄 Conversion needed...")
                success = self.convert_valentini_dataset()
        
        if not success:
            print("❌ Pipeline failed at conversion step")
            return False
        
        # Copy to denoiser directory
        if not self.file_manager.copy_to_denoiser(self.paths['converted'], self.paths['denoiser']):
            print("❌ Pipeline failed at copy step")
            return False
        
        # Generate metadata
        self.generate_metadata_files()
        
        # Create configuration
        self.create_dataset_config()
        
        print("\n🎯 Full pipeline completed successfully!")
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """Print pipeline completion summary"""
        print("\n📋 Pipeline Summary")
        print("=" * 50)
        print(f"Environment: {self.env.upper()}")
        print(f"Dataset path: {self.paths['denoiser']}")
        print(f"Metadata path: {self.paths['egs']}")
        print(f"Config path: {self.paths['config']}")
        print("\n🎯 Next steps:")
        print("1. Review generated files")
        print("2. Start training with the generated configuration")
        print("3. Use the configuration file in your training command")


# ===================================================================
# COMMAND LINE INTERFACE
# ===================================================================

def create_argument_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(description="Multi-Environment Audio Conversion and Metadata Generation")
    
    parser.add_argument("--source_path", type=str,
                       help="Path to source audio dataset (overrides environment default)")
    parser.add_argument("--converted_path", type=str,
                       help="Path to save converted 16kHz audio (overrides environment default)")
    parser.add_argument("--denoiser_path", type=str,
                       help="Path to denoiser dataset directory (overrides environment default)")
    parser.add_argument("--egs_path", type=str,
                       help="Path to save JSON metadata (overrides environment default)")
    parser.add_argument("--config_path", type=str,
                       help="Path to save dataset config (overrides environment default)")
    parser.add_argument("--check_only", action="store_true",
                       help="Only check existing converted data without conversion")
    parser.add_argument("--sample_rate", type=int, default=16000,
                       help="Target sample rate (default: 16000)")
    
    return parser


# ===================================================================
# MAIN EXECUTION
# ===================================================================

if __name__ == "__main__":
    
    # Mac Environment Example (Default)
    print("🍎 Mac Environment Example")
    print("=" * 60)
    
    # Custom paths for Mac (can be modified as needed)
    mac_custom_paths = {
        'original': "/Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5/dataset/valentini_original",
        'converted': "/Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5/dataset/valentini_converted",
        'denoiser': "/Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5/dataset/valentini/",
        'egs': "/Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5/egs/valentini",
        'config': "/Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5/conf/dset/valentini.yaml"
    }
    
    # Initialize converter
    converter = MultiEnvironmentAudioConverter(custom_paths=mac_custom_paths)
    
    # Run full pipeline
    success = converter.run_full_pipeline(check_only=False)
    
    if success:
        print("🎉 Mac pipeline completed successfully!")
    else:
        print("❌ Mac pipeline failed!")
    
    
    # # Google Colab Environment Example (Commented out)
    # print("\n" + "="*60)
    # print("🔬 Google Colab Environment Example (Commented)")
    # print("=" * 60)
    # print("# Uncomment below code when running in Google Colab")
    # print("""
    # # Google Colab paths (using default Config.COLAB_PATHS)
    # colab_custom_paths = {
    #     'original': "/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/original_dataset",
    #     'converted': "/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/converted_data",
    #     'denoiser': "/content/denoiser/dataset/valentini/",
    #     'egs': "/content/denoiser/egs/valentini", 
    #     'config': "/content/denoiser/conf/dset/valentini.yaml"
    # }
    # 
    # # Initialize converter for Colab
    # converter = MultiEnvironmentAudioConverter(custom_paths=colab_custom_paths)
    # 
    # # Run full pipeline
    # success = converter.run_full_pipeline(check_only=False)
    # 
    # if success:
    #     print("🎉 Colab pipeline completed successfully!")
    # else:
    #     print("❌ Colab pipeline failed!")
    # """)
    
    
    # Command line argument parsing (when running as script)
    if len(sys.argv) > 1:
        print("\n" + "="*60)
        print("📝 Command Line Mode")
        print("=" * 60)
        
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Build custom paths from arguments
        custom_paths = {}
        if args.source_path:
            custom_paths['original'] = args.source_path
        if args.converted_path:
            custom_paths['converted'] = args.converted_path
        if args.denoiser_path:
            custom_paths['denoiser'] = args.denoiser_path
        if args.egs_path:
            custom_paths['egs'] = args.egs_path
        if args.config_path:
            custom_paths['config'] = args.config_path
        
        # Initialize converter with custom paths
        cmd_converter = MultiEnvironmentAudioConverter(custom_paths=custom_paths if custom_paths else None)
        
        # Run pipeline
        cmd_success = cmd_converter.run_full_pipeline(check_only=args.check_only)
        
        sys.exit(0 if cmd_success else 1)