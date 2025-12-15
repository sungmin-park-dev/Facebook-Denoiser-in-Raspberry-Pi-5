"""
RP5 Full-Duplex Modular Communication

Features:
- Pluggable audio processors
- Runtime processor switching (Enter key)
- Separate communication and processing logic

Usage:
    python demo/duplex_public_wifi/rp5_full_duplex_modular.py --config configs/rp5a_public.yaml
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

from demo.duplex_public_wifi.core import AudioComm
from demo.duplex_public_wifi.processors import (
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
        buffer_size: int = 30,
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
        # ===== Chunk 크기 증가: 20ms → 60ms =====
        self.chunk_size_48k = 2880  # 960 → 2880 (60ms @ 48kHz)
        # =========================================
        
        # Communication module
        self.comm = AudioComm(
            peer_ip=peer_ip,
            send_port=send_port,
            recv_port=recv_port,
            buffer_size=buffer_size
        )
        
        # Audio processors
        if processors is None:
            processors = [BypassProcessor()]
        self.processors = processors
        self.current_idx = initial_processor
        
        # Queues
        self.send_queue = queue.Queue(maxsize=buffer_size)
        self.recv_queue = queue.Queue(maxsize=buffer_size)
        
        # Stats
        self.packets_sent = 0
        self.packets_received = 0
        self.running = False
        self.start_time = 0
        
        # Audio levels for stats
        self.mic_level = 0.0
        self.processed_level = 0.0
        self.decoded_level = 0.0
        self.speaker_level = 0.0
        
        print(f"✅ FullDuplexModular initialized (Role {role}):")
        print(f"   Mic: Device {mic_device}")
        print(f"   Speaker: Device {speaker_device}")
        print(f"   Buffer: {buffer_size} frames")
        print(f"   Chunk: {self.chunk_size_48k} samples (60ms)")  # ← 변경 표시
        print(f"   Processors: {len(processors)}")
        for i, proc in enumerate(processors):
            prefix = "→" if i == initial_processor else " "
            print(f"   {prefix} [{i}] {proc.get_name()}")
    
    
    def mic_callback(self, indata, frames, time_info, status):
        """Microphone input callback"""
        if status:
            print(f"⚠️  Input: {status}")
        
        try:
            # Convert to mono
            if indata.ndim > 1:
                audio = indata[:, 0].copy()
            else:
                audio = indata.copy()
            
            # Measure level
            self.mic_level = np.abs(audio).max()
            
            # Add to send queue
            self.send_queue.put_nowait(audio)
        except queue.Full:
            pass  # Drop if queue full
    
    
    def speaker_callback(self, outdata, frames, time_info, status):
        """Speaker output callback"""
        if status:
            print(f"⚠️  Output: {status}")
        
        try:
            # Get from receive queue
            audio = self.recv_queue.get_nowait()
            
            # Measure level
            self.speaker_level = np.abs(audio).max()
            
            # Convert mono to stereo
            outdata[:, 0] = audio
            outdata[:, 1] = audio
        except queue.Empty:
            # Output silence if queue empty
            outdata.fill(0)
    
    
    def send_thread(self):
        """Sending thread: Mic → Process → Encode → Send"""
        print("📤 Send thread started")
        
        # 배치 처리용 버퍼
        batch_buffer = []
        batch_size = 1  # 2 → 1: 즉시 처리 (딜레이 최소화)
        
        with sd.InputStream(
            device=self.mic_device,
            channels=2,
            samplerate=self.sample_rate_48k,
            blocksize=self.chunk_size_48k,
            dtype='float32',
            callback=self.mic_callback
        ):
            print("🎤 Microphone started")
            print(f"⚡ Batch processing: {batch_size} chunks (AI processes every {batch_size * 60}ms)")
            
            while self.running:
                try:
                    # ===== Queue 플러시 (딜레이 누적 방지) =====
                    queue_size = self.send_queue.qsize()
                    max_queue_size = 5  # 최대 5개 (300ms)
                    
                    if queue_size > max_queue_size:
                        # 오래된 프레임 버리고 최신 것만 유지
                        dropped = 0
                        while self.send_queue.qsize() > 3:  # 3개(180ms)만 남김
                            self.send_queue.get_nowait()
                            dropped += 1
                        
                        if dropped > 0:
                            print(f"⚠️  Queue overflow: dropped {dropped} frames (RTF spike detected)")
                    # ==========================================
                    
                    # Get audio from mic (2880 samples @ 48kHz)
                    audio_48k = self.send_queue.get(timeout=0.1)
                    
                    # Downsample to 16kHz (2880 → 960 samples)
                    audio_16k = self.comm.downsample_48k_to_16k(audio_48k)
                    
                    # Add to batch buffer
                    batch_buffer.append(audio_16k)
                    
                    # Process when batch is full (or in bypass mode)
                    processor = self.processors[self.current_idx]
                    is_bypass = (self.current_idx == 0)
                    
                    if len(batch_buffer) >= batch_size or is_bypass:
                        # Concatenate batch
                        if len(batch_buffer) > 1:
                            audio_batch = np.concatenate(batch_buffer)
                        else:
                            audio_batch = batch_buffer[0]
                        
                        # Process batch (960 or 1920 samples)
                        audio_processed = processor.process(audio_batch)
                        self.processed_level = np.abs(audio_processed).max()
                        
                        # Split into 320-sample chunks for Opus
                        num_chunks = len(audio_processed) // 320
                        for i in range(num_chunks):
                            chunk_320 = audio_processed[i*320:(i+1)*320]
                            
                            # Send via UDP
                            if self.comm.send(chunk_320):
                                self.packets_sent += 1
                        
                        # Clear batch buffer
                        batch_buffer = []

                except queue.Empty:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"\n❌ Send error: {e}")
                        import traceback
                        traceback.print_exc()
        
        print("\n📤 Send thread stopped")
    
    
    def recv_thread(self):
        """Receiving thread: Receive → Decode → Upsample → Speaker"""
        print("📥 Receive thread started")
        
        # Buffer for accumulating audio to match chunk_size_48k
        audio_buffer = np.array([], dtype=np.float32)
        
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
                    # Receive via UDP (returns 320 samples @ 16kHz)
                    audio_16k = self.comm.receive()
                    self.decoded_level = np.abs(audio_16k).max()
                    
                    # Upsample to 48kHz (320 → 960 samples)
                    audio_48k = self.comm.upsample_16k_to_48k(audio_16k)
                    
                    # Accumulate to buffer
                    audio_buffer = np.concatenate([audio_buffer, audio_48k])
                    
                    # If we have enough samples, send to speaker
                    while len(audio_buffer) >= self.chunk_size_48k:
                        chunk = audio_buffer[:self.chunk_size_48k]
                        audio_buffer = audio_buffer[self.chunk_size_48k:]
                        
                        try:
                            self.recv_queue.put_nowait(chunk)
                        except queue.Full:
                            pass  # Drop if queue full
                    
                except Exception as e:
                    if self.running:
                        print(f"\n❌ Receive error: {e}")
        
        print("\n📥 Receive thread stopped")
    
    
    def toggle_processor(self):
        """Toggle to next processor"""
        self.current_idx = (self.current_idx + 1) % len(self.processors)
        print(f"\n🔄 Switched to: {self.processors[self.current_idx].get_name()}\n")
    
    
    def stats_thread(self):
        """Print statistics periodically"""
        last_tx = 0
        last_rx = 0
        
        while self.running:
            time.sleep(5)
            
            # Calculate rates
            elapsed = time.time() - self.start_time
            tx_rate = (self.packets_sent - last_tx) / 5
            rx_rate = (self.packets_received - last_rx) / 5
            
            last_tx = self.packets_sent
            last_rx = self.packets_received
            
            # Print stats
            print(f"📊 TX: {self.packets_sent:5d} ({tx_rate:.1f}/s) | "
                  f"RX: {self.packets_received:5d} ({rx_rate:.1f}/s) | "
                  f"🎤 {self.mic_level:.3f} | 🔧 {self.processed_level:.3f} | "
                  f"📥 {self.decoded_level:.3f} | 🔊 {self.speaker_level:.3f} | "
                  f"⏱️ {int(elapsed)}s | "
                  f"[{self.processors[self.current_idx].get_name()}] "
                  f"📤Q:{self.send_queue.qsize()}")
    
    
    def input_thread(self):
        """Handle keyboard input for toggling"""
        print("\n🎛️  Press Enter to toggle processor, 'q' + Enter to quit\n")
        
        while self.running:
            try:
                # Check for input without blocking
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    line = sys.stdin.readline().strip()
                    if line == 'q':
                        self.running = False
                        print("\n🛑 Stopping...\n")
                    else:
                        self.toggle_processor()
            except:
                pass
    
    
    def start(self):
        """Start full-duplex communication"""
        self.running = True
        self.start_time = time.time()  # ← 초기화
        
        # Start threads
        send_t = threading.Thread(target=self.send_thread, daemon=True)
        recv_t = threading.Thread(target=self.recv_thread, daemon=True)
        stats_t = threading.Thread(target=self.stats_thread, daemon=True)
        input_t = threading.Thread(target=self.input_thread, daemon=True)
        
        send_t.start()
        recv_t.start()
        stats_t.start()
        input_t.start()
        
        print("\n🔄 Modular full-duplex communication started\n")
        print("Legend: TX=Sent, RX=Recv, 🎤=Mic, 🔧=Processed, 📥=Decoded, 🔊=Speaker")
        
        # Wait for threads
        try:
            while self.running:
                time.sleep(0.1)
                self.packets_received = self.comm.recv_count if hasattr(self.comm, 'recv_count') else 0
        except KeyboardInterrupt:
            self.running = False
            print("\n🛑 Stopping...\n")
        
        # Wait for cleanup
        send_t.join(timeout=2)
        recv_t.join(timeout=2)
        
        # Final stats
        duration = time.time() - self.start_time
        print("\n" + "="*70)
        print("📊 Session Statistics:")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Packets sent: {self.packets_sent} ({self.packets_sent/duration:.1f}/s)")
        print(f"   Packets received: {self.packets_received} ({self.packets_received/duration:.1f}/s)")
        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='RP5 Full-Duplex Modular Communication')
    parser.add_argument('--config', type=str, required=True, help='Config YAML file')
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize processors
    processors = [BypassProcessor()]
    
    if config.get('enable_ai', True):
        model_name = config.get('ai_model', 'Light-32-Depth4')
        processors.append(AIDenoiserProcessor(model_name=model_name))
    
    if config.get('enable_classical', False):
        processors.append(ClassicalFiltersProcessor())
    
    # Create and start
    comm = FullDuplexModular(
        role=config['role'],
        peer_ip=config['peer_ip'],
        mic_device=config['mic_device'],
        speaker_device=config['speaker_device'],
        send_port=config['send_port'],
        recv_port=config['recv_port'],
        buffer_size=config.get('buffer_size', 30),
        processors=processors,
        initial_processor=config.get('initial_processor', 0)
    )
    
    comm.start()


if __name__ == "__main__":
    main()