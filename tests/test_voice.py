import io
import math
import struct
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch


def make_wav(amplitude: int = 0, duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    frames = bytearray()
    count = int(sample_rate * duration)
    for index in range(count):
        sample = int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
        frames.extend(struct.pack("<h", sample))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return output.getvalue()


class VoiceTests(unittest.TestCase):
    def test_audio_signal_stats_detect_silent_recording(self):
        from modules.voice import audio_signal_stats

        stats = audio_signal_stats(make_wav())
        self.assertTrue(stats["parseable"])
        self.assertTrue(stats["is_silent"])

    def test_transcription_stops_before_api_for_silent_recording(self):
        from modules.voice import VoiceCaptureError, transcribe_audio

        with patch("modules.voice._get_client") as get_client, patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaises(VoiceCaptureError):
                transcribe_audio(make_wav())
        get_client.assert_not_called()

    def test_transcription_sends_detected_audio_as_wav(self):
        from modules.voice import transcribe_audio

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(text="测试语音")
                )
            )
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "测试语音")

    def test_transcription_sends_webm_mime_and_browser_meter_stats(self):
        from modules.voice import transcribe_audio

        calls = {}

        def create(**kwargs):
            calls.update(kwargs)
            return SimpleNamespace(text="开放麦克风测试")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(
                b"webm-audio",
                "answer.webm",
                client_stats={"duration_seconds": 4.2, "rms": 0.04, "peak": 0.2},
            )

        self.assertEqual(result, "开放麦克风测试")
        self.assertEqual(calls["file"][0], "answer.webm")
        self.assertEqual(calls["file"][2], "audio/webm")

    def test_transcription_passes_english_language_for_reading(self):
        from modules.voice import transcribe_audio

        calls = {}

        def create(**kwargs):
            calls.update(kwargs)
            return SimpleNamespace(text="grain boundaries influence metals")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "reading.wav", language="en")

        self.assertEqual(result, "grain boundaries influence metals")
        self.assertEqual(calls["language"], "en")


if __name__ == "__main__":
    unittest.main()
