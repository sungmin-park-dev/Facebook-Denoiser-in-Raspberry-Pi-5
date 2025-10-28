"""
Mac Audio Sender (Server)

Captures microphone input → AI Denoising → Opus encoding → UDP transmission

Usage:
    python scripts/mac_sender.py --rp5-ip 192.168.1.101 --port 5000
"""

import argparse
import socket
import numpy as np
import sounddevice as sd
import torch
from scipy import signal
from pathlib import Path
import sys
import queue
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.communication.codec import OpusCodec
from audio_pipeline.core.model_loader import ModelLoader


class MacAudioSender:
    """Mac-based audio sender with AI denoising"""
    
    def __init__(
        self,
        rp5_ip: str,
        rp5_port: int,
        mic_device: int = None,
        model_name: str = "Light-32-Depth4"
    ):
        """
        Initialize Mac audio sender
        
        Args:
            rp5_ip: RP5 IP address
            rp5_port: RP5 UDP port
            mic_device: Microphone device index (None = default)
            model_name: AI denoiser model name
        """
        self.rp5_ip = rp5_ip
        self.rp5_port = rp5_port
        
        # Audio settings
        self.sample_rate_48k = 48000
        self.sample_rate_16k = 16000
        self.chunk_size_48k = 960   # 20ms @ 48kHz
        self.chunk_size_16k = 320   # 20ms @ 16kHz
        
        # UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Opus codec
        self.codec = OpusCodec(
            sample_rate=self.sample_rate_16k,
            channels=1,
            bitrate=16000,
            frame_duration=20
        )
        
        # AI Denoiser
        print(f"🤖 Loading {model_name}...")
        self.denoiser = ModelLoader.load(model_name)
        self.denoiser.eval()
        
        # Audio queue
        self.audio_queue = queue.Queue()
        
        # Microphone device
        self.mic_device = mic_device
        
        # Stats
        self.packets_sent = 0
        self.start_time = None
        
        print(f"✅ MacAudioSender initialized:")
        print(f"   Target: {rp5_ip}:{rp5_port}")
        print(f"   Mic device: {mic_device if mic_device else 'default'}")
        print(f"   Model: {model_name}")
    
    def audio_callback(self, indata, frames, time_info, status):
        """Audio input callback - runs in separate thread"""
        if status:
            print(f"⚠️ Audio status: {status}")
        
        # Add to queue (non-blocking)
        try:
            self.audio_queue.put(indata.copy(), block=False)
        except queue.Full:
            print("⚠️ Audio queue full, dropping frame")
    
    def process_and_send(self):
        """Main processing loop"""
        print("🎙️ Starting audio capture...")
        
        with sd.InputStream(
            device=self.mic_device,
            channels=1,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.audio_callback
        ):
            self.start_time = time.time()
            
            print(f"📡 Sending to {self.rp5_ip}:{self.rp5_port}")
            print("Press Ctrl+C to stop...\n")
            
            try:
                while True:
                    # Get audio from queue
                    audio_48k = self.audio_queue.get()
                    
                    # 48kHz → 16kHz
                    audio_16k = signal.resample_poly(
                        audio_48k.flatten(), 1, 3
                    ).astype(np.float32)
                    
                    # AI Denoising
                    with torch.no_grad():
                        audio_tensor = torch.from_numpy(audio_16k).unsqueeze(0).unsqueeze(0)
                        denoised = self.denoiser(audio_tensor)
                        denoised_audio = denoised.squeeze().cpu().numpy()
                    
                    # Opus encoding
                    packet = self.codec.encode(denoised_audio)
                    
                    # UDP transmission
                    self.socket.sendto(packet, (self.rp5_ip, self.rp5_port))
                    
                    self.packets_sent += 1
                    
                    # Stats (every 5 seconds)
                    if self.packets_sent % 250 == 0:  # 250 packets = 5 sec @ 20ms/packet
                        elapsed = time.time() - self.start_time
                        print(f"📊 Sent {self.packets_sent} packets in {elapsed:.1f}s")
            
            except KeyboardInterrupt:
                print("\n🛑 Stopping...")
                self.print_stats()
    
    def print_stats(self):
        """Print final statistics"""
        elapsed = time.time() - self.start_time
        print("\n" + "="*60)
        print("📊 Session Statistics:")
        print(f"   Packets sent: {self.packets_sent}")
        print(f"   Duration: {elapsed:.1f}s")
        print(f"   Average rate: {self.packets_sent/elapsed:.1f} packets/s")
        print("="*60)


def list_audio_devices():
    """List all available audio devices"""
    print("\n🎤 Available Audio Devices:")
    print("="*60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"{i}: {device['name']}")
            print(f"   Channels: {device['max_input_channels']}")
            print(f"   Sample Rate: {device['default_samplerate']}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Mac Audio Sender")
    parser.add_argument("--rp5-ip", type=str, required=True,
                       help="RP5 IP address (e.g., 192.168.1.101)")
    parser.add_argument("--port", type=int, default=5000,
                       help="UDP port (default: 5000)")
    parser.add_argument("--device", type=int, default=None,
                       help="Microphone device index (see --list-devices)")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices and exit")
    parser.add_argument("--model", type=str, default="Light-32-Depth4",
                       help="AI denoiser model name")
    
    args = parser.parse_args()
    
    if args.list_devices:
        list_audio_devices()
        return
    
    # Create and start sender
    sender = MacAudioSender(
        rp5_ip=args.rp5_ip,
        rp5_port=args.port,
        mic_device=args.device,
        model_name=args.model
    )
    
    sender.process_and_send()


if __name__ == "__main__":
    main()