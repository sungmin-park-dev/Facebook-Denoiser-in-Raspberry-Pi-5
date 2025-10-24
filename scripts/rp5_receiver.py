"""
RP5 Audio Receiver (Client)

Receives UDP packets → Opus decoding → Speaker output

Usage:
    python scripts/rp5_receiver.py --port 5000 --device 1
"""

import argparse
import socket
import numpy as np
import sounddevice as sd
from pathlib import Path
import sys
import queue
import time
from collections import deque

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.communication.codec import OpusCodec


class RP5AudioReceiver:
    """RP5-based audio receiver"""
    
    def __init__(
        self,
        port: int,
        speaker_device: int = 1,
        buffer_size: int = 10
    ):
        """
        Initialize RP5 audio receiver
        
        Args:
            port: UDP listening port
            speaker_device: Speaker device index
            buffer_size: Jitter buffer size (number of frames)
        """
        self.port = port
        self.speaker_device = speaker_device
        
        # Audio settings
        self.sample_rate_48k = 48000
        self.sample_rate_16k = 16000
        self.chunk_size_48k = 960   # 20ms @ 48kHz
        self.chunk_size_16k = 320   # 20ms @ 16kHz
        
        # UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))  # Listen on all interfaces
        self.socket.settimeout(0.1)  # 100ms timeout for non-blocking
        
        # Opus codec
        self.codec = OpusCodec(
            sample_rate=self.sample_rate_16k,
            channels=1,
            bitrate=16000,
            frame_duration=20
        )
        
        # Jitter buffer (protect against packet loss)
        self.jitter_buffer = deque(maxlen=buffer_size)
        self.output_queue = queue.Queue(maxsize=50)
        
        # Stats
        self.packets_received = 0
        self.packets_lost = 0
        self.start_time = None
        
        print(f"✅ RP5AudioReceiver initialized:")
        print(f"   Listening on port: {port}")
        print(f"   Speaker device: {speaker_device}")
        print(f"   Buffer size: {buffer_size} frames")
    
    def audio_callback(self, outdata, frames, time_info, status):
        """Audio output callback - runs in separate thread"""
        if status:
            print(f"⚠️ Audio status: {status}")
        
        try:
            # Get audio from queue
            audio = self.output_queue.get_nowait()
            outdata[:] = audio.reshape(-1, 1)
        except queue.Empty:
            # Buffer underrun - output silence
            outdata.fill(0)
            print("⚠️ Buffer underrun - outputting silence")
    
    def receive_and_play(self):
        """Main receive loop"""
        print(f"👂 Listening on port {self.port}...")
        
        with sd.OutputStream(
            device=self.speaker_device,
            channels=1,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.audio_callback
        ):
            self.start_time = time.time()
            
            print("Press Ctrl+C to stop...\n")
            
            try:
                while True:
                    try:
                        # Receive UDP packet
                        packet, addr = self.socket.recvfrom(4096)
                        
                        # First packet
                        if self.packets_received == 0:
                            print(f"📡 Connected to {addr[0]}:{addr[1]}")
                        
                        self.packets_received += 1
                        
                        # Opus decoding
                        audio_16k = self.codec.decode(packet)
                        
                        # 16kHz → 48kHz (using scipy)
                        from scipy import signal
                        audio_48k = signal.resample_poly(
                            audio_16k, 3, 1
                        ).astype(np.float32)
                        
                        # Add to output queue
                        try:
                            self.output_queue.put(audio_48k, block=False)
                        except queue.Full:
                            print("⚠️ Output queue full, dropping frame")
                        
                        # Stats (every 5 seconds)
                        if self.packets_received % 250 == 0:
                            elapsed = time.time() - self.start_time
                            print(f"📊 Received {self.packets_received} packets in {elapsed:.1f}s")
                    
                    except socket.timeout:
                        # No packet received (timeout)
                        pass
            
            except KeyboardInterrupt:
                print("\n🛑 Stopping...")
                self.print_stats()
    
    def print_stats(self):
        """Print final statistics"""
        elapsed = time.time() - self.start_time
        print("\n" + "="*60)
        print("📊 Session Statistics:")
        print(f"   Packets received: {self.packets_received}")
        print(f"   Duration: {elapsed:.1f}s")
        print(f"   Average rate: {self.packets_received/elapsed:.1f} packets/s")
        print("="*60)


def list_audio_devices():
    """List all available audio devices"""
    print("\n🔊 Available Audio Devices:")
    print("="*60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            print(f"{i}: {device['name']}")
            print(f"   Channels: {device['max_output_channels']}")
            print(f"   Sample Rate: {device['default_samplerate']}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="RP5 Audio Receiver")
    parser.add_argument("--port", type=int, default=5000,
                       help="UDP listening port (default: 5000)")
    parser.add_argument("--device", type=int, default=1,
                       help="Speaker device index (default: 1 for H08A)")
    parser.add_argument("--buffer", type=int, default=10,
                       help="Jitter buffer size in frames (default: 10)")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices and exit")
    
    args = parser.parse_args()
    
    if args.list_devices:
        list_audio_devices()
        return
    
    # Create and start receiver
    receiver = RP5AudioReceiver(
        port=args.port,
        speaker_device=args.device,
        buffer_size=args.buffer
    )
    
    receiver.receive_and_play()


if __name__ == "__main__":
    main()