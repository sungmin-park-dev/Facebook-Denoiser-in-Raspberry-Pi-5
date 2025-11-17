"""
RP5 Full-Duplex Modular Communication

Features:
- Pluggable audio processors
- Runtime processor switching (Enter key)
- Separate communication and processing logic

Usage:
    python demo/duplex/rp5_full_duplex_modular.py --config configs/rp5a_modular.yaml
"""

import argparse
import numpy as np
import sounddevice as sd
from pathlib import Path
import sys
import queue
import time
import threading
import yaml
import select

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from demo.duplex.core import AudioComm
from demo.duplex.processors import (
    BypassProcessor,
    AIDenoiserProcessor,
    ClassicalFiltersProcessor
)


class FullDuplexModular:
    """Full-duplex communication with modular processors"""
    
    def __init__(
        self,
        role: str,
        peer_ip: str,
        mic_device: int,
        speaker_device: int,
        send_port: int,
        recv_port: int,
        buffer_size: int = 5,
        processors: list = None,
        initial_processor: int = 0
    ):
        """
        Initialize modular full-duplex communication
        
        Args:
            role: 'A' or 'B'
            peer_ip: Peer IP address
            mic_device: Microphone device index
            speaker_device: Speaker device index
            send_port: UDP sending port
            recv_port: UDP receiving port
            buffer_size: Queue buffer size (increase for hotspot host)
            processors: List of AudioProcessor instances
            initial_processor: Initial processor index
        """
        self.role = role
        self.mic_device = mic_device
        self.speaker_device = speaker_device
        
        # Audio settings
        self.sample_rate_48k = 48000
        self.chunk_size_48k = 960  # 20ms
        
        # Communication module
        self.comm = AudioComm(
            peer_ip=peer_ip,
            send_port=send_port,
            recv_port=recv_port,
            buffer_size=buffer_size
        )
        
        # Audio processors
        self.processors = processors or [BypassProcessor()]
        self.current_idx = initial_processor
        
        # Audio queues
        self.send_queue = queue.Queue(maxsize=buffer_size)
        self.recv_queue = queue.Queue(maxsize=buffer_size)
        
        # Stats
        self.packets_sent = 0
        self.packets_received = 0
        self.start_time = None
        self.running = True
        
        # Levels for monitoring
        self.mic_level = 0.0
        self.processed_level = 0.0
        self.decoded_level = 0.0
        self.speaker_level = 0.0
        
        print(f"✅ FullDuplexModular initialized (Role {role}):")
        print(f"   Mic: Device {mic_device}")
        print(f"   Speaker: Device {speaker_device}")
        print(f"   Buffer: {buffer_size} frames")
        print(f"   Processors: {len(self.processors)}")
        for i, p in enumerate(self.processors):
            marker = "→" if i == initial_processor else " "
            print(f"   {marker} [{i}] {p.get_name()}")
    
    def mic_callback(self, indata, frames, time_info, status):
        """Microphone input callback"""
        if status:
            print(f"⚠️ Mic: {status}")
        
        try:
            mono = indata.mean(axis=1, keepdims=True)
            self.mic_level = np.abs(mono).max()
            self.send_queue.put(mono, block=False)
        except queue.Full:
            pass
    
    def speaker_callback(self, outdata, frames, time_info, status):
        """Speaker output callback"""
        if status:
            print(f"⚠️ Speaker: {status}")
        
        try:
            mono_data = self.recv_queue.get(block=False)
            stereo_data = np.repeat(mono_data, 2, axis=1)
            self.speaker_level = np.abs(stereo_data).max()
            outdata[:] = stereo_data
        except queue.Empty:
            outdata.fill(0)
    
    def send_thread(self):
        """Sending thread: Mic → Process → Encode → Send"""
        print("📤 Send thread started")
        
        with sd.InputStream(
            device=self.mic_device,
            channels=2,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.mic_callback
        ):
            print("🎤 Microphone started")
            
            while self.running:
                try:
                    # Get audio from mic
                    audio_48k = self.send_queue.get(timeout=0.1)
                    
                    # Downsample to 16kHz
                    audio_16k = self.comm.downsample_48k_to_16k(audio_48k)
                    
                    # Process with current processor ()
                    # processor = self.processors[self.current_idx]
                    # audio_processed = processor.process(audio_16k)
                    # self.processed_level = np.abs(audio_processed).max()
                    
                    # # Send via UDP
                    # if self.comm.send(audio_processed):
                    #     self.packets_sent += 1

                    #### 수정 ####
                    # 🔧 AI 제거: 원본 전송
                    self.processed_level = np.abs(audio_16k).max()
                    
                    if self.comm.send(audio_16k):  # audio_processed → audio_16k
                        self.packets_sent += 1

                    
                except queue.Empty:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"\n❌ Send error: {e}")
        
        print("\n📤 Send thread stopped")
    
    def recv_thread(self):
        """Receiving thread: Receive → Decode → Upsample → Speaker"""
        print("📥 Receive thread started")
        
        with sd.OutputStream(
            device=self.speaker_device,
            channels=2,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.speaker_callback
        ):
            print("🔊 Speaker started")
            
            while self.running:
                try:
                    # Receive via UDP
                    audio_16k = self.comm.receive()

                    # 🔧 AI 추가: Opus 해제 후 처리
                    if self.current_idx > 0:  # AI 모드일 때만
                        processor = self.processors[self.current_idx]
                        audio_16k = processor.process(audio_16k)

                    self.decoded_level = np.abs(audio_16k).max()
                    
                    # Upsample to 48kHz
                    audio_48k = self.comm.upsample_16k_to_48k(audio_16k)
                    
                    # Add to speaker queue
                    self.recv_queue.put(audio_48k.reshape(-1, 1), block=False)
                    self.packets_received += 1
                    
                except queue.Full:
                    pass
                except Exception as e:
                    if self.running:
                        print(f"\n❌ Receive error: {e}")
        
        print("\n📥 Receive thread stopped")
    
    def toggle_thread(self):
        """Processor toggle listener"""
        print("\n🎛️  Press Enter to toggle processor, 'q' + Enter to quit")
        
        while self.running:
            if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                line = sys.stdin.readline().strip().lower()
                
                if line == 'q':
                    print("\n👋 Quit requested...")
                    self.running = False
                    break
                else:
                    # Toggle processor
                    self.current_idx = (self.current_idx + 1) % len(self.processors)
                    processor = self.processors[self.current_idx]
                    print(f"\n🔄 Switched to: {processor.get_name()}\n")
    
    def stats_thread(self):
        """Statistics reporting"""
        last_update = time.time()
        
        while self.running:
            time.sleep(1)
            if self.running and (time.time() - last_update) >= 1.0:
                elapsed = time.time() - self.start_time
                send_rate = self.packets_sent / elapsed if elapsed > 0 else 0
                recv_rate = self.packets_received / elapsed if elapsed > 0 else 0
                
                processor_name = self.processors[self.current_idx].get_name()
                
                status = (
                    f"\r📊 TX: {self.packets_sent:5d} ({send_rate:4.1f}/s) | "
                    f"RX: {self.packets_received:5d} ({recv_rate:4.1f}/s) | "
                    f"🎤 {self.mic_level:.3f} | "
                    f"🔧 {self.processed_level:.3f} | "
                    f"📥 {self.decoded_level:.3f} | "
                    f"🔊 {self.speaker_level:.3f} | "
                    f"⏱️ {elapsed:.0f}s | "
                    f"[{processor_name}] 📥RX-AI"  # ← 이 부분 추가
                )
                print(status, end='', flush=True)
                last_update = time.time()
    
    def run(self):
        """Start full-duplex communication"""
        self.start_time = time.time()
        
        # Start threads
        send_t = threading.Thread(target=self.send_thread, daemon=True)
        recv_t = threading.Thread(target=self.recv_thread, daemon=True)
        toggle_t = threading.Thread(target=self.toggle_thread, daemon=True)
        stats_t = threading.Thread(target=self.stats_thread, daemon=True)
        
        send_t.start()
        recv_t.start()
        toggle_t.start()
        stats_t.start()
        
        print("\n🔄 Modular full-duplex communication started")
        print("Legend: TX=Sent, RX=Recv, 🎤=Mic, 🔧=Processed, 📥=Decoded, 🔊=Speaker")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping...")
            self.running = False
            
            send_t.join(timeout=2)
            recv_t.join(timeout=2)
            
            # Final stats
            elapsed = time.time() - self.start_time
            print("\n" + "="*70)
            print("📊 Session Statistics:")
            print(f"   Duration: {elapsed:.1f}s")
            print(f"   Packets sent: {self.packets_sent} ({self.packets_sent/elapsed:.1f}/s)")
            print(f"   Packets received: {self.packets_received} ({self.packets_received/elapsed:.1f}/s)")
            print("="*70)
            
            # Close communication
            self.comm.close()


def list_audio_devices():
    """List audio devices"""
    print("\n🎤🔊 Available Audio Devices:")
    print("="*60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        in_ch = device['max_input_channels']
        out_ch = device['max_output_channels']
        if in_ch > 0 or out_ch > 0:
            print(f"{i}: {device['name']}")
            print(f"   Input: {in_ch} ch, Output: {out_ch} ch")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="RP5 Modular Full-Duplex")
    parser.add_argument("--config", type=str, required=True,
                       help="Config file path")
    parser.add_argument("--list-devices", action="store_true",
                       help="List audio devices")
    
    args = parser.parse_args()
    
    if args.list_devices:
        list_audio_devices()
        return
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize processors
    processors = []
    
    # Add Bypass
    processors.append(BypassProcessor())
    
    # Add AI Denoiser (if enabled)
    if config.get('enable_ai', True):
        try:
            processors.append(AIDenoiserProcessor(
                model_name=config.get('ai_model', 'Light-32-Depth4')
            ))
        except Exception as e:
            print(f"⚠️ Failed to load AI model: {e}")
    
    # Add Classical Filters (if enabled)
    if config.get('enable_classical', False):
        processors.append(ClassicalFiltersProcessor())
    
    # Create and run
    comm = FullDuplexModular(
        role=config['role'],
        peer_ip=config['peer_ip'],
        mic_device=config['mic_device'],
        speaker_device=config['speaker_device'],
        send_port=config['send_port'],
        recv_port=config['recv_port'],
        buffer_size=config.get('buffer_size', 5),
        processors=processors,
        initial_processor=config.get('initial_processor', 0)
    )
    
    comm.run()


if __name__ == "__main__":
    main()
