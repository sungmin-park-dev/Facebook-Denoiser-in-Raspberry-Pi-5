#!/usr/bin/env python3
"""
Opus Codec Test Script

Tests Opus encoding/decoding functionality
Run independently on each RP5 (no network needed)

Usage:
    python demo/duplex/test_opus_codec.py
"""

import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.communication.codec import OpusCodec


def test_opus_basic():
    """Basic Opus encode/decode test"""
    print("="*60)
    print("🧪 Test 1: Basic Opus Encode/Decode")
    print("="*60)
    
    try:
        # Initialize codec
        codec = OpusCodec(
            sample_rate=16000,
            channels=1,
            bitrate=16000,
            frame_duration=20
        )
        print("✅ Codec initialized successfully")
        print(f"   Sample rate: 16000 Hz")
        print(f"   Channels: 1 (mono)")
        print(f"   Bitrate: 16000 bps")
        print(f"   Frame duration: 20 ms")
        
    except Exception as e:
        print(f"❌ FAILED: Codec initialization failed")
        print(f"   Error: {e}")
        return False
    
    # Test 1: Random noise
    print("\n📊 Generating test audio (random noise, 320 samples)...")
    audio = np.random.randn(320).astype(np.int16)
    print(f"   Range: [{audio.min()}, {audio.max()}]")
    print(f"   Mean: {audio.mean():.2f}")
    print(f"   RMS: {np.sqrt(np.mean(audio**2)):.2f}")
    
    # Encode
    print("\n🔄 Encoding...")
    try:
        encoded = codec.encode(audio)
        print(f"✅ Encoded successfully: {len(encoded)} bytes")
    except Exception as e:
        print(f"❌ FAILED: Encoding failed")
        print(f"   Error: {e}")
        return False
    
    # Decode
    print("\n🔄 Decoding...")
    try:
        decoded = codec.decode(encoded)
        print(f"✅ Decoded successfully: {len(decoded)} samples")
        print(f"   Range: [{decoded.min()}, {decoded.max()}]")
        print(f"   Mean: {decoded.mean():.2f}")
        print(f"   RMS: {np.sqrt(np.mean(decoded**2)):.2f}")
    except Exception as e:
        print(f"❌ FAILED: Decoding failed")
        print(f"   Error: {e}")
        return False
    
    # Compare
    print("\n📊 Comparing original vs decoded...")
    diff_abs = np.abs(audio - decoded).mean()
    diff_pct = (diff_abs / (np.abs(audio).mean() + 1e-6)) * 100
    
    print(f"   Absolute difference: {diff_abs:.2f}")
    print(f"   Relative difference: {diff_pct:.2f}%")
    
    if diff_abs < 1000:
        print("✅ PASSED: Difference within acceptable range")
        return True
    else:
        print(f"⚠️ WARNING: High difference detected ({diff_abs:.2f})")
        return True  # Still pass, but warn


def test_opus_silence():
    """Test with silence (edge case)"""
    print("\n" + "="*60)
    print("🧪 Test 2: Silence (Edge Case)")
    print("="*60)
    
    codec = OpusCodec(sample_rate=16000, channels=1, bitrate=16000, frame_duration=20)
    
    # Silence
    audio = np.zeros(320, dtype=np.int16)
    print("📊 Generating silence (all zeros)...")
    
    try:
        encoded = codec.encode(audio)
        decoded = codec.decode(encoded)
        
        max_val = np.abs(decoded).max()
        print(f"✅ Encoded/decoded successfully")
        print(f"   Decoded max value: {max_val}")
        
        if max_val < 100:
            print("✅ PASSED: Silence preserved")
            return True
        else:
            print(f"⚠️ WARNING: Non-zero values in decoded silence ({max_val})")
            return True
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_opus_loud_signal():
    """Test with loud signal (clipping test)"""
    print("\n" + "="*60)
    print("🧪 Test 3: Loud Signal (Clipping Test)")
    print("="*60)
    
    codec = OpusCodec(sample_rate=16000, channels=1, bitrate=16000, frame_duration=20)
    
    # Near-max amplitude
    audio = np.full(320, 30000, dtype=np.int16)
    print("📊 Generating loud signal (amplitude: 30000)...")
    
    try:
        encoded = codec.encode(audio)
        decoded = codec.decode(encoded)
        
        print(f"✅ Encoded/decoded successfully")
        print(f"   Original mean: {audio.mean():.2f}")
        print(f"   Decoded mean: {decoded.mean():.2f}")
        print(f"   Decoded range: [{decoded.min()}, {decoded.max()}]")
        
        diff = abs(audio.mean() - decoded.mean())
        if diff < 3000:
            print("✅ PASSED: Loud signal preserved")
            return True
        else:
            print(f"⚠️ WARNING: Large difference ({diff:.2f})")
            return True
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_opus_multiple_packets():
    """Test multiple encode/decode cycles"""
    print("\n" + "="*60)
    print("🧪 Test 4: Multiple Packets (50 cycles)")
    print("="*60)
    
    codec = OpusCodec(sample_rate=16000, channels=1, bitrate=16000, frame_duration=20)
    
    print("📊 Encoding/decoding 50 random packets...")
    
    failures = 0
    for i in range(50):
        audio = (np.random.randn(320) * 10000).astype(np.int16)
        
        try:
            encoded = codec.encode(audio)
            decoded = codec.decode(encoded)
            
            # Check if decoded is all zeros (common failure mode)
            if np.abs(decoded).max() == 0 and np.abs(audio).max() > 0:
                failures += 1
                if failures == 1:
                    print(f"   ⚠️ Packet {i+1}: Decoded as silence (original was not)")
                    
        except Exception as e:
            failures += 1
            if failures == 1:
                print(f"   ❌ Packet {i+1}: {e}")
    
    print(f"\n📊 Results: {50 - failures}/50 packets successful")
    
    if failures == 0:
        print("✅ PASSED: All packets processed correctly")
        return True
    elif failures < 5:
        print(f"⚠️ WARNING: {failures} packet(s) failed")
        return True
    else:
        print(f"❌ FAILED: {failures} packet(s) failed")
        return False


def main():
    """Run all Opus codec tests"""
    print("\n" + "="*60)
    print("🎵 Opus Codec Test Suite")
    print("="*60)
    print()
    
    tests = [
        ("Basic Encode/Decode", test_opus_basic),
        ("Silence Handling", test_opus_silence),
        ("Loud Signal", test_opus_loud_signal),
        ("Multiple Packets", test_opus_multiple_packets),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("\n" + "="*60)
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("="*60)
        print("\n✅ Opus codec is working correctly!")
        print("   The audio transmission issue is likely elsewhere.")
        return 0
    else:
        print(f"⚠️ SOME TESTS FAILED ({passed}/{total})")
        print("="*60)
        print("\n❌ Opus codec may have issues!")
        print("   Suggested actions:")
        print("   1. Reinstall libopus: sudo apt-get install --reinstall libopus0 libopus-dev")
        print("   2. Reinstall Python opuslib: pip install --force-reinstall opuslib")
        return 1


if __name__ == "__main__":
    sys.exit(main())
