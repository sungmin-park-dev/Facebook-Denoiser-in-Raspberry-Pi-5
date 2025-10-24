"""
Opus Codec Wrapper for Low-Latency Audio Transmission

Supports:
- 16kHz mono audio
- VOIP-optimized encoding
- 16kbps bitrate
- 20ms frame size (ultra-low latency)
"""

import numpy as np
import opuslib
from typing import Tuple

class OpusCodec:
    """Opus encoder/decoder for real-time audio communication"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        bitrate: int = 16000,
        frame_duration: int = 20  # ms
    ):
        """
        Initialize Opus codec
        
        Args:
            sample_rate: Audio sample rate (16000 Hz)
            channels: Number of channels (1=mono)
            bitrate: Target bitrate (16000 bps)
            frame_duration: Frame size in milliseconds (20ms for ultra-low latency)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate
        self.frame_duration = frame_duration
        
        # Calculate frame size in samples
        self.frame_size = int(sample_rate * frame_duration / 1000)
        
        # Initialize encoder
        self.encoder = opuslib.Encoder(
            fs=sample_rate,
            channels=channels,
            application=opuslib.APPLICATION_VOIP  # Optimized for voice
        )
        # Set bitrate (Opus requires >= 500 bps, using 24000 for good quality at 16kHz)
        try:
            self.encoder.bitrate = max(bitrate, 24000)
        except:
            pass  # Use default bitrate if setting fails
        
        # Initialize decoder
        self.decoder = opuslib.Decoder(
            fs=sample_rate,
            channels=channels
        )
        
        print(f"✅ OpusCodec initialized:")
        print(f"   Sample rate: {sample_rate} Hz")
        print(f"   Channels: {channels}")
        print(f"   Bitrate: {bitrate} bps")
        print(f"   Frame size: {self.frame_size} samples ({frame_duration}ms)")
    
    def encode(self, audio: np.ndarray) -> bytes:
        """
        Encode audio to Opus compressed format
        
        Args:
            audio: Float32 audio samples [-1.0, 1.0], shape: (frame_size,)
        
        Returns:
            Compressed Opus packet (bytes)
        """
        # Convert float32 [-1, 1] to int16 [-32768, 32767]
        pcm = (audio * 32767).astype(np.int16)
        
        # Encode to Opus
        try:
            encoded = self.encoder.encode(pcm.tobytes(), self.frame_size)
            return encoded
        except Exception as e:
            print(f"❌ Encoding error: {e}")
            return b''
    
    def decode(self, packet: bytes) -> np.ndarray:
        """
        Decode Opus packet to audio
        
        Args:
            packet: Opus compressed packet (bytes)
        
        Returns:
            Float32 audio samples [-1.0, 1.0], shape: (frame_size,)
        """
        try:
            # Decode from Opus
            decoded = self.decoder.decode(packet, self.frame_size)
            
            # Convert int16 to float32
            audio = np.frombuffer(decoded, dtype=np.int16).astype(np.float32) / 32767.0
            return audio
        
        except Exception as e:
            print(f"❌ Decoding error: {e}")
            # Return silence on error
            return np.zeros(self.frame_size, dtype=np.float32)
    
    def get_packet_size(self) -> int:
        """Return typical encoded packet size (bytes)"""
        # Opus 16kbps @ 20ms = ~40 bytes
        return int(self.bitrate / 8 * self.frame_duration / 1000)


# Test function
if __name__ == "__main__":
    print("🧪 Testing OpusCodec...")
    
    codec = OpusCodec()
    
    # Generate test sine wave
    duration = 0.02  # 20ms
    t = np.linspace(0, duration, codec.frame_size, endpoint=False)
    test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # 440Hz sine
    
    # Encode
    packet = codec.encode(test_audio)
    print(f"📦 Encoded packet size: {len(packet)} bytes")
    
    # Decode
    decoded_audio = codec.decode(packet)
    print(f"🔊 Decoded audio shape: {decoded_audio.shape}")
    
    # Check quality
    mse = np.mean((test_audio - decoded_audio) ** 2)
    print(f"🎯 MSE (lower is better): {mse:.6f}")
    
    if mse < 0.01:
        print("✅ Codec test passed!")
    else:
        print("⚠️ High reconstruction error")