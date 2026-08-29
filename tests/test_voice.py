import io
import math
import struct
import unittest
import wave
import inspect
import os
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
    def test_stt_model_candidates_preserve_model_names(self):
        from modules.voice import _stt_model_candidates

        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "Qwen/Qwen3-ASR-1.7B",
                "SILICONFLOW_STT_FALLBACK_MODELS": "FunAudioLLM/SenseVoiceSmall,XingChenAGI/XingChenASR-V3.2",
            },
        ):
            self.assertEqual(
                _stt_model_candidates(),
                [
                    "Qwen/Qwen3-ASR-1.7B",
                    "FunAudioLLM/SenseVoiceSmall",
                    "XingChenAGI/XingChenASR-V3.2",
                ],
            )

    def test_transcription_switches_to_configured_fallback_model_after_503(self):
        from modules.voice import transcribe_audio

        calls = []

        class Temporary503Error(RuntimeError):
            status_code = 503

        def create(**kwargs):
            calls.append(kwargs["model"])
            if kwargs["model"] == "primary-asr":
                raise Temporary503Error("service unavailable")
            return SimpleNamespace(text="备用模型识别成功")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "0",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "备用模型识别成功")
        self.assertEqual(calls, ["primary-asr", "fallback-asr"])

    def test_transcription_switches_to_fallback_when_primary_model_is_missing(self):
        from modules.voice import transcribe_audio

        calls = []

        class MissingModelError(RuntimeError):
            status_code = 404

        def create(**kwargs):
            calls.append(kwargs["model"])
            if kwargs["model"] == "primary-asr":
                raise MissingModelError("model not found")
            return SimpleNamespace(text="模型切换成功")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "3",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "模型切换成功")
        self.assertEqual(calls, ["primary-asr", "fallback-asr"])

    def test_transcription_switches_model_when_primary_returns_empty_text(self):
        from modules.voice import transcribe_audio

        calls = []

        def create(**kwargs):
            calls.append(kwargs["model"])
            text = "" if kwargs["model"] == "primary-asr" else "备用模型识别成功"
            return SimpleNamespace(text=text)

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "0",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "备用模型识别成功")
        self.assertEqual(calls, ["primary-asr", "fallback-asr"])

    def test_transcription_switches_model_when_primary_returns_only_fillers(self):
        from modules.voice import transcribe_audio

        calls = []

        def create(**kwargs):
            calls.append(kwargs["model"])
            text = "嗯嗯啊" if kwargs["model"] == "primary-asr" else "备用模型识别成功"
            return SimpleNamespace(text=text)

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "0",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "备用模型识别成功")
        self.assertEqual(calls, ["primary-asr", "fallback-asr"])

    def test_transcription_reports_empty_response_after_all_models_fail(self):
        from modules.voice import VoiceCaptureError, transcribe_audio

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(text=""))
            )
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "0",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaisesRegex(VoiceCaptureError, "空文本"):
                transcribe_audio(make_wav(amplitude=8000), "answer.wav")

    def test_transcription_preserves_503_when_later_fallback_is_empty(self):
        from modules.voice import VoiceCaptureError, transcribe_audio

        class Temporary503Error(RuntimeError):
            status_code = 503

        def create(**kwargs):
            if kwargs["model"] == "primary-asr":
                return SimpleNamespace(text="")
            raise Temporary503Error("service unavailable")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "0",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaisesRegex(VoiceCaptureError, "503"):
                transcribe_audio(make_wav(amplitude=8000), "answer.wav")

    def test_transcription_preserves_503_when_primary_fails_and_fallback_is_empty(self):
        """A later empty response must not hide the provider outage."""
        from modules.voice import VoiceCaptureError, transcribe_audio

        class Temporary503Error(RuntimeError):
            status_code = 503

        def create(**kwargs):
            if kwargs["model"] == "primary-asr":
                raise Temporary503Error("service unavailable")
            return SimpleNamespace(text="")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(
            os.environ,
            {
                "SILICONFLOW_STT_MODEL": "primary-asr",
                "SILICONFLOW_STT_FALLBACK_MODELS": "fallback-asr",
                "SILICONFLOW_STT_MAX_RETRIES": "0",
            },
        ), patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaisesRegex(VoiceCaptureError, "503"):
                transcribe_audio(make_wav(amplitude=8000), "answer.wav")

    def test_transcription_retries_temporary_503_then_succeeds(self):
        from modules.voice import transcribe_audio

        calls = {"count": 0}

        class Temporary503Error(RuntimeError):
            status_code = 503

        def create(**kwargs):
            calls["count"] += 1
            if calls["count"] < 3:
                raise Temporary503Error("service unavailable")
            return SimpleNamespace(text="恢复后的语音")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch.dict(os.environ, {"SILICONFLOW_STT_MAX_RETRIES": "2"}), patch(
            "modules.voice._get_client", return_value=fake_client
        ), patch("modules.voice._log_audio_event"), patch("modules.voice.time.sleep") as sleep:
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "恢复后的语音")
        self.assertEqual(calls["count"], 3)
        self.assertEqual(sleep.call_count, 2)

    def test_transcription_raises_when_cleanup_removes_all_text(self):
        """Filler-only ASR output must expose a retry path instead of success."""
        from modules.voice import EmptyTranscriptionError, transcribe_audio

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(text="嗯嗯啊"))
            )
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaisesRegex(EmptyTranscriptionError, "停顿词"):
                transcribe_audio(make_wav(amplitude=8000), "answer.wav")

    def test_transcription_total_deadline_is_checked_before_call(self):
        from modules.voice import TranscriptionDeadlineExceeded, _create_transcription_with_retry

        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text="不应被调用")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with self.assertRaisesRegex(TranscriptionDeadlineExceeded, "总时限"):
            _create_transcription_with_retry(
                fake_client,
                {"model": "primary-asr", "file": ("answer.wav", b"audio", "audio/wav")},
                deadline=0.0,
            )
        self.assertEqual(calls, [])

    def test_transcription_reports_clear_error_after_503_retries(self):
        from modules.voice import VoiceCaptureError, transcribe_audio

        class Temporary503Error(RuntimeError):
            status_code = 503

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=lambda **kwargs: (_ for _ in ()).throw(Temporary503Error("service unavailable"))
                )
            )
        )
        with patch.dict(os.environ, {"SILICONFLOW_STT_MAX_RETRIES": "1"}), patch(
            "modules.voice._get_client", return_value=fake_client
        ), patch("modules.voice._log_audio_event"), patch("modules.voice.time.sleep"):
            with self.assertRaisesRegex(VoiceCaptureError, "503"):
                transcribe_audio(make_wav(amplitude=8000), "answer.wav")

    def test_clean_transcript_filters_hesitations_and_normalizes_material_terms(self):
        from modules.voice import clean_transcript

        result = clean_transcript(
            "嗯嗯，这个晶界面啊会影响奥氏体钢的性能。",
            language="zh",
        )

        self.assertEqual(result["text"], "这个晶界会影响奥氏体不锈钢的性能")
        self.assertEqual(result["raw_text"], "嗯嗯，这个晶界面啊会影响奥氏体钢的性能。")
        self.assertEqual(result["fillers_removed"], ["嗯嗯", "啊"])
        self.assertEqual(
            [item["to"] for item in result["term_corrections"]],
            ["晶界", "奥氏体不锈钢"],
        )

    def test_clean_transcript_handles_english_hesitations_and_hyphenation(self):
        from modules.voice import clean_transcript

        result = clean_transcript(
            "uh um grain-boundaries improve thin films.",
            language="en",
            term_hints=["grain boundary", "thin film"],
        )

        self.assertEqual(result["text"], "grain boundaries improve thin films")
        self.assertEqual(result["fillers_removed"], ["uh", "um"])
        self.assertIn("grain boundary", result["recognized_terms"])
        self.assertIn("thin film", result["recognized_terms"])

    def test_clean_transcript_does_not_remove_normal_chinese_content(self):
        from modules.voice import clean_transcript

        result = clean_transcript("这个材料的性能很重要。", language="zh")

        self.assertEqual(result["text"], "这个材料的性能很重要")
        self.assertEqual(result["fillers_removed"], [])

    def test_build_stt_prompt_contains_material_term_hints(self):
        from modules.voice import build_stt_prompt

        prompt = build_stt_prompt(["grain boundary", "thin film"], language="en")

        self.assertIn("grain boundary", prompt)
        self.assertIn("thin film", prompt)
        self.assertIn("Materials-science", prompt)

    def test_recorder_defaults_to_ten_minute_safety_limit(self):
        from modules.voice import audio_recorder

        self.assertEqual(inspect.signature(audio_recorder).parameters["max_seconds"].default, 600)

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

    def test_transcription_sets_bounded_provider_timeout(self):
        """A stalled ASR request must not leave the Streamlit run hanging."""
        from modules.voice import transcribe_audio

        calls = {}

        def create(**kwargs):
            calls.update(kwargs)
            return SimpleNamespace(text="有界超时")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(make_wav(amplitude=8000), "answer.wav")

        self.assertEqual(result, "有界超时")
        self.assertIn("timeout", calls)
        self.assertGreaterEqual(float(calls["timeout"]), 10.0)
        self.assertLessEqual(float(calls["timeout"]), 180.0)

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

    def test_transcription_returns_cleaned_text_and_metadata(self):
        from modules.voice import transcribe_audio

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(text="嗯嗯 晶界面 啊")
                )
            )
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(
                make_wav(amplitude=8000),
                "answer.wav",
                term_hints=["grain boundary"],
                return_metadata=True,
            )

        self.assertIsInstance(result, dict)
        self.assertEqual(result["text"], "晶界")
        self.assertEqual(result["raw_text"], "嗯嗯 晶界面 啊")
        self.assertEqual(result["fillers_removed"], ["嗯嗯", "啊"])
        self.assertIn("晶界", result["recognized_terms"])

    def test_transcription_retries_without_prompt_for_unsupported_provider(self):
        from modules.voice import transcribe_audio

        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            if "prompt" in kwargs:
                raise RuntimeError("unknown field: prompt")
            return SimpleNamespace(text="晶界")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(
                make_wav(amplitude=8000),
                "answer.wav",
                term_hints=["grain boundary"],
            )

        self.assertEqual(result, "晶界")
        self.assertEqual(len(calls), 2)
        self.assertIn("prompt", calls[0])
        self.assertNotIn("prompt", calls[1])

    def test_transcription_retries_without_prompt_for_validation_error(self):
        from modules.voice import transcribe_audio

        calls = []

        class ValidationError(RuntimeError):
            status_code = 400

        def create(**kwargs):
            calls.append(kwargs)
            if "prompt" in kwargs:
                raise ValidationError("invalid prompt field")
            return SimpleNamespace(text="开放麦克风语音")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(
                make_wav(amplitude=8000),
                "answer.wav",
                term_hints=["晶界"],
            )

        self.assertEqual(result, "开放麦克风语音")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("prompt", calls[1])

    def test_transcription_does_not_hide_unrelated_validation_error(self):
        from modules.voice import transcribe_audio

        calls = []

        class ValidationError(RuntimeError):
            status_code = 400

        def create(**kwargs):
            calls.append(kwargs)
            raise ValidationError("invalid audio file")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaises(ValidationError):
                transcribe_audio(
                    make_wav(amplitude=8000),
                    "answer.wav",
                    term_hints=["晶界"],
                )

        self.assertEqual(len(calls), 1)
        self.assertIn("prompt", calls[0])

    def test_transcription_rejects_silent_browser_recording_using_client_meter(self):
        from modules.voice import VoiceCaptureError, transcribe_audio

        with patch("modules.voice._get_client") as get_client, patch(
            "modules.voice._log_audio_event"
        ):
            with self.assertRaises(VoiceCaptureError):
                transcribe_audio(
                    b"silent-webm",
                    "answer.webm",
                    client_stats={"duration_seconds": 19.4, "rms": 0.0, "peak": 0.0},
                )
        get_client.assert_not_called()

    def test_transcription_allows_possible_driver_audio_when_meter_is_unavailable(self):
        from modules.voice import transcribe_audio

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(text="driver audio")
                )
            )
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(
                b"x" * 20000,
                "answer.webm",
                client_stats={"duration_seconds": 4.0, "rms": 0.0, "peak": 0.0},
            )
        self.assertEqual(result, "driver audio")

    def test_transcription_uses_server_wav_signal_when_browser_meter_is_zero(self):
        from modules.voice import transcribe_audio

        calls = {}

        def create(**kwargs):
            calls.update(kwargs)
            return SimpleNamespace(text="wav signal")

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        with patch("modules.voice._get_client", return_value=fake_client), patch(
            "modules.voice._log_audio_event"
        ):
            result = transcribe_audio(
                make_wav(amplitude=8000, duration=1.0),
                "answer.wav",
                client_stats={"duration_seconds": 1.0, "rms": 0.0, "peak": 0.0},
            )
        self.assertEqual(result, "wav signal")
        self.assertEqual(calls["file"][2], "audio/wav")


if __name__ == "__main__":
    unittest.main()
