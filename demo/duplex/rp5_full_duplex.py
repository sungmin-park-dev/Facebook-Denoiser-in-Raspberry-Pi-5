"""
RP5 Full-Duplex Audio Communication

Simultaneous bidirectional audio with AI denoising

Usage:
    # RP5-A (Role A) - Recommended: Use config file
    python demo/duplex/rp5_full_duplex.py --config demo/duplex/configs/rp5a_config.yaml
    
    # RP5-B (Role B) - Recommended: Use config file
    python demo/duplex/rp5_full_duplex.py --config demo/duplex/configs/rp5b_config.yaml
    
    # Alternative: Manual parameters
    # RP5-A
    python demo/duplex/rp5_full_duplex.py --role A --peer-ip 10.42.0.224 --mic-device 1 --speaker-device 1
    
    # RP5-B
    python demo/duplex/rp5_full_duplex.py --role B --peer-ip 10.42.0.1 --mic-device 1 --speaker-device 1
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
import threading
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.communication.codec import OpusCodec
from audio_pipeline.core.model_loader import ModelLoader


class FullDuplexComm:
    """Full-duplex audio communication with AI denoising"""
    
    def __init__(
        self,
        role: str,
        peer_ip: str,
        mic_device: int,
        speaker_device: int,
        send_port: int = 9998,
        recv_port: int = 9999,
        model_name: str = "Light-32-Depth4"
    ):
        """
        Initialize full-duplex communication
        
        Args:
            role: 'A' or 'B'
            peer_ip: Peer RP5 IP address
            mic_device: Microphone device index
            speaker_device: Speaker device index
            send_port: UDP sending port
            recv_port: UDP receiving port
            model_name: AI denoiser model name
        """
        self.role = role
        self.peer_ip = peer_ip
        self.mic_device = mic_device
        self.speaker_device = speaker_device
        
        # Port assignment (A and B use opposite ports)
        if role == 'A':
            self.send_port = send_port
            self.recv_port = recv_port
        else:  # role == 'B'
            self.send_port = recv_port  # Swap
            self.recv_port = send_port
        
        # Audio settings
        self.sample_rate_48k = 48000
        self.sample_rate_16k = 16000
        self.chunk_size_48k = 960   # 20ms @ 48kHz
        self.chunk_size_16k = 320   # 20ms @ 16kHz
        
        # UDP sockets
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket.bind(('0.0.0.0', self.recv_port))
        self.recv_socket.settimeout(0.1)
        
        # Opus codec
        self.codec = OpusCodec(
            sample_rate=self.sample_rate_16k,
            channels=1,
            bitrate=16000,
            frame_duration=20
        )
        
        # AI Denoiser (for sending)
        print(f"🤖 Loading {model_name}...")
        self.denoiser = ModelLoader.load(model_name)
        self.denoiser.eval()
        
        # Audio queues
        self.send_queue = queue.Queue(maxsize=5)  # Smaller for lower latency
        self.recv_queue = queue.Queue(maxsize=5)
        
        # Stats
        self.packets_sent = 0
        self.packets_received = 0
        self.start_time = None
        self.running = True
        
        print(f"✅ FullDuplexComm initialized (Role {role}):")
        print(f"   Peer: {peer_ip}")
        print(f"   Sending: {peer_ip}:{self.send_port}")
        print(f"   Receiving: 0.0.0.0:{self.recv_port}")
        print(f"   Mic: Device {mic_device}")
        print(f"   Speaker: Device {speaker_device}")
        print(f"   Model: {model_name}")
    
    def mic_callback(self, indata, frames, time_info, status):
        """Microphone input callback"""
        if status:
            print(f"⚠️ Mic status: {status}")
        
        try:
            # Convert stereo to mono (average both channels)
            mono = indata.mean(axis=1, keepdims=True)
            self.send_queue.put(mono, block=False)
        except queue.Full:
            pass  # Drop frame if queue full
    
    def speaker_callback(self, outdata, frames, time_info, status):
        """Speaker output callback"""
        if status:
            print(f"⚠️ Speaker status: {status}")
        
        try:
            mono_data = self.recv_queue.get(block=False)
            # Convert mono to stereo (duplicate to both channels)
            outdata[:] = np.repeat(mono_data, 2, axis=1)
        except queue.Empty:
            outdata.fill(0)  # Silence if no data
    
    def send_thread(self):
        """Sending thread: Mic → AI → Encode → UDP"""
        print("📤 Send thread started")
        
        # Resampler (48kHz → 16kHz)
        resample_ratio = self.sample_rate_16k / self.sample_rate_48k
        
        with sd.InputStream(
            device=self.mic_device,
            channels=2,  # H08A requires stereo (converted to mono in callback)
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.mic_callback
        ):
            while self.running:
                try:
                    # Get audio from mic
                    audio_48k = self.send_queue.get(timeout=0.1)
                    
                    # Downsample 48kHz → 16kHz
                    num_samples_16k = int(len(audio_48k) * resample_ratio)
                    audio_16k = signal.resample(audio_48k, num_samples_16k)
                    
                    # AI Denoising
                    with torch.no_grad():
                        # Flatten to 1D if needed (handle 2D resampling output)
                        audio_16k_flat = audio_16k.flatten() if audio_16k.ndim > 1 else audio_16k
                        # Shape: [batch=1, channels=1, time]
                        audio_tensor = torch.from_numpy(audio_16k_flat).float().unsqueeze(0).unsqueeze(0)
                        denoised = self.denoiser(audio_tensor)
                        audio_denoised = denoised.squeeze().cpu().numpy()
                    
                    # Opus encode
                    audio_int16 = np.clip(audio_denoised * 32767, -32768, 32767).astype(np.int16)
                    encoded = self.codec.encode(audio_int16)
                    
                    # UDP send
                    self.send_socket.sendto(encoded, (self.peer_ip, self.send_port))
                    self.packets_sent += 1
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"❌ Send error: {e}")
        
        print("📤 Send thread stopped")
    
    def recv_thread(self):
        """Receiving thread: UDP → Decode → Upsample → Speaker"""
        print("📥 Receive thread started")
        
        # Resampler (16kHz → 48kHz)
        resample_ratio = self.sample_rate_48k / self.sample_rate_16k
        
        with sd.OutputStream(
            device=self.speaker_device,
            channels=2,  # H08A requires stereo (mono expanded in callback)
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.speaker_callback
        ):
            while self.running:
                try:
                    # UDP receive
                    data, addr = self.recv_socket.recvfrom(4096)
                    
                    # Opus decode
                    audio_int16 = self.codec.decode(data)
                    audio_16k = audio_int16.astype(np.float32) / 32767.0
                    
                    # Upsample 16kHz → 48kHz
                    num_samples_48k = int(len(audio_16k) * resample_ratio)
                    audio_48k = signal.resample(audio_16k, num_samples_48k)
                    
                    # Add to speaker queue
                    self.recv_queue.put(audio_48k.reshape(-1, 1), block=False)
                    self.packets_received += 1
                    
                except socket.timeout:
                    continue
                except queue.Full:
                    pass  # Drop if queue full
                except Exception as e:
                    if self.running:
                        print(f"❌ Receive error: {e}")
        
        print("📥 Receive thread stopped")
    
    def stats_thread(self):
        """Statistics reporting thread"""
        while self.running:
            time.sleep(5)
            if self.running:
                elapsed = time.time() - self.start_time
                print(f"📊 Sent: {self.packets_sent}, Recv: {self.packets_received} ({elapsed:.1f}s)")
    
    def run(self):
        """Start full-duplex communication"""
        self.start_time = time.time()
        
        # Start threads
        send_t = threading.Thread(target=self.send_thread, daemon=True)
        recv_t = threading.Thread(target=self.recv_thread, daemon=True)
        stats_t = threading.Thread(target=self.stats_thread, daemon=True)
        
        send_t.start()
        recv_t.start()
        stats_t.start()
        
        print("\n🔄 Full-duplex communication started")
        print("Press Ctrl+C to stop...\n")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
            self.running = False
            
            # Wait for threads
            send_t.join(timeout=2)
            recv_t.join(timeout=2)
            
            # Print final stats
            elapsed = time.time() - self.start_time
            print("="*60)
            print("📊 Session Statistics:")
            print(f"   Packets sent: {self.packets_sent}")
            print(f"   Packets received: {self.packets_received}")
            print(f"   Duration: {elapsed:.1f}s")
            print(f"   Send rate: {self.packets_sent/elapsed:.1f} packets/s")
            print(f"   Recv rate: {self.packets_received/elapsed:.1f} packets/s")
            print("="*60)


def list_audio_devices():
    """List all available audio devices"""
    print("\n🎤🔊 Available Audio Devices:")
    print("="*60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        in_ch = device['max_input_channels']
        out_ch = device['max_output_channels']
        if in_ch > 0 or out_ch > 0:
            print(f"{i}: {device['name']}")
            print(f"   Input: {in_ch} ch, Output: {out_ch} ch")
            print(f"   Sample Rate: {device['default_samplerate']}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="RP5 Full-Duplex Communication")
    parser.add_argument("--config", type=str, default=None,
                       help="Config file path (e.g., configs/rp5a_config.yaml)")
    parser.add_argument("--role", type=str, required=False, choices=['A', 'B'],
                       help="Role: A or B")
    parser.add_argument("--peer-ip", type=str, required=False,
                       help="Peer RP5 IP address")
    parser.add_argument("--mic-device", type=int, required=False,
                       help="Microphone device index")
    parser.add_argument("--speaker-device", type=int, required=False,
                       help="Speaker device index")
    parser.add_argument("--send-port", type=int, default=9998,
                       help="UDP sending port (default: 9998)")
    parser.add_argument("--recv-port", type=int, default=9999,
                       help="UDP receiving port (default: 9999)")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices and exit")
    parser.add_argument("--model", type=str, default="Light-32-Depth4",
                       help="AI denoiser model name")
    
    args = parser.parse_args()
    
    # Load config file if provided
    if args.config:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
        # Override with config file values (command line args take precedence)
        args.role = args.role or config.get('role')
        args.peer_ip = args.peer_ip or config.get('peer_ip')
        args.mic_device = args.mic_device if args.mic_device is not None else config.get('mic_device')
        args.speaker_device = args.speaker_device if args.speaker_device is not None else config.get('speaker_device')
        args.send_port = config.get('send_port', args.send_port)
        args.recv_port = config.get('recv_port', args.recv_port)
        args.model = config.get('model', args.model)
        
        print(f"📄 Loaded config from: {args.config}")
    
    if args.list_devices:
        list_audio_devices()
        return
    
    # Validate required arguments
    if not args.role:
        parser.error("--role is required (or provide via config file)")
    if not args.peer_ip:
        parser.error("--peer-ip is required (or provide via config file)")
    if args.mic_device is None:
        parser.error("--mic-device is required (or provide via config file)")
    if args.speaker_device is None:
        parser.error("--speaker-device is required (or provide via config file)")
    
    # Create and start full-duplex comm
    comm = FullDuplexComm(
        role=args.role,
        peer_ip=args.peer_ip,
        mic_device=args.mic_device,
        speaker_device=args.speaker_device,
        send_port=args.send_port,
        recv_port=args.recv_port,
        model_name=args.model
    )
    
    comm.run()


if __name__ == "__main__":
    main()