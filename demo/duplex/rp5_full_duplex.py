"""
RP5 Full-Duplex Audio Communication - Improved Output Version

Changelog:
- Dynamic updates for audio levels and stats (single line refresh)
- Static output for important events only
- Cleaner terminal output
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
project_root = Path(__file__).resolve().parents[2]
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
        """Initialize full-duplex communication"""
        self.role = role
        self.peer_ip = peer_ip
        self.mic_device = mic_device
        self.speaker_device = speaker_device
        
        # Port assignment (use as configured in YAML)
        self.send_port = send_port
        self.recv_port = recv_port
        
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
        self.send_queue = queue.Queue(maxsize=5)
        self.recv_queue = queue.Queue(maxsize=5)
        
        # Stats
        self.packets_sent = 0
        self.packets_received = 0
        self.start_time = None
        self.running = True
        
        # Audio levels for display
        self.mic_level = 0.0
        self.ai_before = 0.0
        self.ai_after = 0.0
        self.decoded_level = 0.0
        self.speaker_level = 0.0
        
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
            print(f"\n⚠️ Mic status: {status}")
        
        try:
            # Convert stereo to mono
            mono = indata.mean(axis=1, keepdims=True)
            
            # Update level
            self.mic_level = np.abs(mono).max()
            
            # Add to send queue
            self.send_queue.put(mono, block=False)
        except queue.Full:
            pass
    
    def speaker_callback(self, outdata, frames, time_info, status):
        """Speaker output callback"""
        if status:
            print(f"\n⚠️ Speaker status: {status}")
        
        try:
            # Get from receive queue
            mono_data = self.recv_queue.get_nowait()
            
            # Update level
            self.speaker_level = np.abs(mono_data).max()
            
            # Convert mono to stereo
            outdata[:] = np.repeat(mono_data, 2, axis=1)
        except queue.Empty:
            outdata.fill(0)
    
    def send_thread(self):
        """Audio sending thread"""
        resample_ratio = self.sample_rate_16k / self.sample_rate_48k
        
        with sd.InputStream(
            device=self.mic_device,
            channels=2,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            callback=self.mic_callback
        ):
            print("🎤 Microphone started")
            
            while self.running:
                try:
                    # Get audio from mic queue
                    audio_48k = self.send_queue.get(timeout=0.1)
                    
                    # Downsample 48kHz → 16kHz
                    num_samples_16k = int(len(audio_48k) * resample_ratio)
                    audio_16k = signal.resample(audio_48k, num_samples_16k)
                    
                    # AI Denoising
                    with torch.no_grad():
                        audio_torch = torch.from_numpy(audio_16k.T).float().unsqueeze(0)
                        self.ai_before = audio_torch.abs().max().item()
                        
                        denoised = self.denoiser(audio_torch)
                        self.ai_after = denoised.abs().max().item()
                        
                        audio_16k_clean = denoised.squeeze(0).T.numpy()
                    
                    # Opus encode
                    audio_int16 = (audio_16k_clean * 32767).astype(np.int16)
                    packet = self.codec.encode(audio_int16)
                    
                    # UDP send
                    self.send_socket.sendto(packet, (self.peer_ip, self.send_port))
                    self.packets_sent += 1
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"\n❌ Send error: {e}")
        
        print("\n🎤 Microphone stopped")
    
    def recv_thread(self):
        """Audio receiving thread"""
        resample_ratio = self.sample_rate_48k / self.sample_rate_16k
        
        with sd.OutputStream(
            device=self.speaker_device,
            channels=2,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            callback=self.speaker_callback
        ):
            print("🔊 Speaker started")
            
            while self.running:
                try:
                    # UDP receive
                    data, addr = self.recv_socket.recvfrom(4096)
                    
                    # Opus decode
                    audio_int16 = self.codec.decode(data)
                    audio_16k = audio_int16.astype(np.float32) / 32767.0
                    
                    # Update level
                    self.decoded_level = np.abs(audio_16k).max()
                    
                    # Upsample 16kHz → 48kHz
                    num_samples_48k = int(len(audio_16k) * resample_ratio)
                    audio_48k = signal.resample(audio_16k, num_samples_48k)
                    
                    # Add to speaker queue
                    self.recv_queue.put(audio_48k.reshape(-1, 1), block=False)
                    self.packets_received += 1
                    
                except socket.timeout:
                    continue
                except queue.Full:
                    pass
                except Exception as e:
                    if self.running:
                        print(f"\n❌ Receive error: {e}")
        
        print("\n📥 Receive thread stopped")
    
    def stats_thread(self):
        """Statistics reporting thread with dynamic updates"""
        last_update = time.time()
        
        while self.running:
            current_time = time.time()
            
            # Update every 0.5 seconds
            if current_time - last_update >= 0.5:
                elapsed = current_time - self.start_time
                send_rate = self.packets_sent / elapsed if elapsed > 0 else 0
                recv_rate = self.packets_received / elapsed if elapsed > 0 else 0
                
                # Single line dynamic update
                status = (
                    f"\r📊 TX: {self.packets_sent:5d} ({send_rate:4.1f} pkt/s) | "
                    f"RX: {self.packets_received:5d} ({recv_rate:4.1f} pkt/s) | "
                    f"🎤 {self.mic_level:.3f} | "
                    f"🤖 {self.ai_before:.3f}→{self.ai_after:.3f} | "
                    f"📥 {self.decoded_level:.3f} | "
                    f"🔊 {self.speaker_level:.3f} | "
                    f"⏱️ {elapsed:.0f}s"
                )
                
                print(status, end='', flush=True)
                last_update = current_time
            
            time.sleep(0.1)
    
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
        print("Legend: TX=Sent, RX=Received, 🎤=Mic, 🤖=AI(before→after), 📥=Decoded, 🔊=Speaker")
        print("Press Ctrl+C to stop...\n")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping...")
            self.running = False
            
            # Wait for threads
            send_t.join(timeout=2)
            recv_t.join(timeout=2)
            
            # Print final stats
            elapsed = time.time() - self.start_time
            print("\n" + "="*70)
            print("📊 Session Statistics:")
            print(f"   Packets sent: {self.packets_sent}")
            print(f"   Packets received: {self.packets_received}")
            print(f"   Duration: {elapsed:.1f}s")
            print(f"   Send rate: {self.packets_sent/elapsed:.1f} packets/s")
            print(f"   Recv rate: {self.packets_received/elapsed:.1f} packets/s")
            print("="*70)


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
                       help="Config file path")
    parser.add_argument("--role", type=str, required=False, choices=['A', 'B'],
                       help="Role: A or B")
    parser.add_argument("--peer-ip", type=str, required=False,
                       help="Peer RP5 IP address")
    parser.add_argument("--mic-device", type=int, required=False,
                       help="Microphone device index")
    parser.add_argument("--speaker-device", type=int, required=False,
                       help="Speaker device index")
    parser.add_argument("--send-port", type=int, default=9998,
                       help="UDP sending port")
    parser.add_argument("--recv-port", type=int, default=9999,
                       help="UDP receiving port")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices and exit")
    parser.add_argument("--model", type=str, default="Light-32-Depth4",
                       help="AI denoiser model name")
    
    args = parser.parse_args()
    
    # Load config file if provided
    if args.config:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
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
        parser.error("--role is required")
    if not args.peer_ip:
        parser.error("--peer-ip is required")
    if args.mic_device is None:
        parser.error("--mic-device is required")
    if args.speaker_device is None:
        parser.error("--speaker-device is required")
    
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
