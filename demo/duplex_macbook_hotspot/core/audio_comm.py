"""
Audio Communication Module

Handles UDP transmission, Opus codec, and resampling
"""

import socket
import numpy as np
from scipy import signal
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from src.communication.codec import OpusCodec


class AudioComm:
    """
    Audio communication handler
    
    Responsibilities:
    - UDP socket management
    - Opus encoding/decoding
    - 48kHz ↔ 16kHz resampling
    """
    
    def __init__(
        self,
        peer_ip: str,
        send_port: int,
        recv_port: int,
        buffer_size: int = 5
    ):
        """
        Initialize audio communication
        
        Args:
            peer_ip: Peer device IP address
            send_port: UDP port for sending
            recv_port: UDP port for receiving
            buffer_size: Not used here (kept for compatibility)
        """
        self.peer_ip = peer_ip
        self.send_port = send_port
        self.recv_port = recv_port
        
        # Audio settings
        self.sample_rate_48k = 48000
        self.sample_rate_16k = 16000
        
        # UDP sockets
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # ===== UDP 수신 버퍼 크기 증가 =====
        # 기본값: ~200KB
        # 증가값: 1MB (약 50초 분량의 오디오)
        UDP_RECV_BUFFER = 1024 * 1024  # 1MB
        
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, UDP_RECV_BUFFER)
        self.recv_socket.bind(('0.0.0.0', self.recv_port))
        self.recv_socket.settimeout(0.1)
        
        # 실제 설정된 버퍼 크기 확인
        actual_buffer = self.recv_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        print(f"📡 UDP receive buffer: {actual_buffer / 1024:.0f} KB")
        # ===================================
        
        # Opus codec
        self.codec = OpusCodec(
            sample_rate=self.sample_rate_16k,
            channels=1,
            bitrate=16000,
            frame_duration=20
        )
        
        # Resample ratios
        self.downsample_ratio = self.sample_rate_16k / self.sample_rate_48k
        self.upsample_ratio = self.sample_rate_48k / self.sample_rate_16k
        
        # ===== 패킷 손실 모니터링 =====
        self.timeout_count = 0
        self.recv_count = 0
        self._loss_log_interval = 500  # 500번마다 손실률 출력
        # ============================
        
        print(f"✅ AudioComm initialized:")
        print(f"   Peer: {peer_ip}")
        print(f"   Send: {peer_ip}:{send_port}")
        print(f"   Recv: 0.0.0.0:{recv_port}")
    

    def downsample_48k_to_16k(self, audio_48k: np.ndarray) -> np.ndarray:
        """
        Downsample from 48kHz to 16kHz using polyphase filter
        
        Args:
            audio_48k: Audio at 48kHz
        
        Returns:
            Audio at 16kHz (float32, mono)
        """
        # Flatten if needed
        if audio_48k.ndim > 1:
            audio_48k = audio_48k.flatten()
        
        # Measure input level
        input_level = np.abs(audio_48k).max()
        
        # Polyphase resampling: 48kHz → 16kHz (down by 3)
        audio_16k = signal.resample_poly(audio_48k, 1, 3)
        
        # Measure output level
        output_level = np.abs(audio_16k).max()
        
        # Gain compensation
        if output_level > 1e-6 and input_level > 1e-6:
            gain = input_level / (output_level + 1e-8)
            gain = np.clip(gain, 0.5, 2.0)
            audio_16k = audio_16k * gain
        
        return audio_16k.astype(np.float32)
    
    
    def upsample_16k_to_48k(self, audio_16k: np.ndarray) -> np.ndarray:
        """
        Upsample from 16kHz to 48kHz using polyphase filter
        
        Args:
            audio_16k: Audio at 16kHz
        
        Returns:
            Audio at 48kHz (float32, mono)
        """
        # Polyphase resampling: 16kHz → 48kHz (up by 3)
        audio_48k = signal.resample_poly(audio_16k, 3, 1)
        
        return audio_48k.astype(np.float32)
    

    
    def send(self, audio_16k: np.ndarray) -> bool:
        """
        Send audio via UDP
        
        Args:
            audio_16k: Audio at 16kHz (float32, [-1, 1])
        
        Returns:
            True if sent successfully
        """
        try:
            # Opus encode (expects float32 [-1, 1])
            packet = self.codec.encode(audio_16k)
            
            # UDP send
            self.send_socket.sendto(packet, (self.peer_ip, self.send_port))
            return True
            
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False
    
    def receive(self) -> np.ndarray:
        """
        Receive audio via UDP
        
        Returns:
            Audio at 16kHz (float32, [-1, 1])
            Returns zeros on timeout/error
        """
        try:
            # UDP receive
            data, addr = self.recv_socket.recvfrom(4096)
            
            # Opus decode (returns float32 [-1, 1])
            audio_16k = self.codec.decode(data)
            
            # ===== 수신 카운트 =====
            self.recv_count += 1
            # ======================
            
            return audio_16k
            
        except socket.timeout:
            # ===== Timeout 카운트 =====
            self.timeout_count += 1
            
            # 주기적으로 손실률 출력
            if (self.recv_count + self.timeout_count) % self._loss_log_interval == 0:
                total = self.recv_count + self.timeout_count
                loss_rate = (self.timeout_count / total) * 100 if total > 0 else 0
                print(f"📡 Packet loss: {self.timeout_count}/{total} ({loss_rate:.1f}%)")
            # =========================
            
            # Return silence on timeout
            return np.zeros(320, dtype=np.float32)
        except Exception as e:
            print(f"❌ Receive error: {e}")
            return np.zeros(320, dtype=np.float32)
    
    def close(self):
        """Close sockets"""
        self.send_socket.close()
        self.recv_socket.close()
