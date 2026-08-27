"""
语音能力
========
使用浏览器录音，再通过当前配置的 OpenAI 兼容接口进行语音转文字。
默认模型为硅基流动的 SenseVoiceSmall；面试官语音播报由浏览器 SpeechSynthesis 完成，
因此不需要额外的 TTS API Key。
"""

import base64
import binascii
import io
import os
import json
import time
import math
import struct
import wave
from pathlib import Path
from typing import Optional

from modules.api_client import _get_client


DEFAULT_STT_MODEL = "FunAudioLLM/SenseVoiceSmall"
_AUDIO_RECORDER_COMPONENT = None


class VoiceCaptureError(ValueError):
    """The recording cannot be usefully sent to speech recognition."""


def _pcm_signal_levels(frames: bytes, sample_width: int) -> tuple[float, float]:
    """Return RMS and peak for little-endian PCM without the removed audioop API."""
    if sample_width == 1:
        values = (sample - 128 for sample in frames)
    elif sample_width in (2, 4):
        count = len(frames) // sample_width
        if not count:
            return 0.0, 0.0
        values = struct.unpack("<{}{}".format(count, "h" if sample_width == 2 else "i"), frames[: count * sample_width])
    elif sample_width == 3:
        values_list = []
        for offset in range(0, len(frames) - 2, 3):
            value = frames[offset] | (frames[offset + 1] << 8) | (frames[offset + 2] << 16)
            if value & 0x800000:
                value -= 0x1000000
            values_list.append(value)
        values = iter(values_list)
    else:
        return 0.0, 0.0

    count = 0
    sum_squares = 0.0
    peak = 0
    for value in values:
        count += 1
        sum_squares += value * value
        peak = max(peak, abs(value))
    if not count:
        return 0.0, 0.0
    full_scale = float(1 << (8 * sample_width - 1))
    return math.sqrt(sum_squares / count) / full_scale, peak / full_scale


def audio_recorder(
    *,
    label: str = "🎙️ 录音回答（可选）",
    key: str,
    max_seconds: int = 600,
    open_microphone: bool = True,
    audio_mode: str = "auto",
) -> Optional[dict]:
    """Render the microphone recorder with explicit browser audio constraints.

    ``st.audio_input`` does not expose ``echoCancellation`` or
    ``noiseSuppression``. The local component does, and returns a compact JSON
    envelope whose audio payload is decoded here before it reaches the STT API.
    ``None`` means that the component has not produced a recording yet.
    """
    global _AUDIO_RECORDER_COMPONENT
    if _AUDIO_RECORDER_COMPONENT is None:
        from streamlit.components.v1 import declare_component

        component_path = Path(__file__).resolve().parent.parent / "components" / "audio_recorder"
        if not (component_path / "index.html").is_file():
            raise VoiceCaptureError("录音组件文件缺失，请重新安装项目文件后重试。")
        _AUDIO_RECORDER_COMPONENT = declare_component(
            "ai_interview_audio_recorder",
            path=str(component_path),
        )

    value = _AUDIO_RECORDER_COMPONENT(
        label=label,
        max_seconds=max(5, min(int(max_seconds), 600)),
        open_microphone=bool(open_microphone),
        audio_mode=str(audio_mode or "auto"),
        default=None,
        key=key,
    )
    if not isinstance(value, dict) or value.get("status") != "recorded":
        return None

    encoded = value.get("audio_base64")
    if not encoded:
        raise VoiceCaptureError("录音内容为空，请点击“重新录音”再试一次。")
    try:
        audio_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise VoiceCaptureError("录音编码无效，请刷新页面后重新录音。") from exc
    if not audio_bytes:
        raise VoiceCaptureError("录音内容为空，请点击“重新录音”再试一次。")

    filename = Path(str(value.get("filename") or "answer.webm")).name
    suffix = Path(filename).suffix.lower()
    if suffix not in (".wav", ".mp3", ".m4a", ".webm", ".mp4", ".ogg"):
        filename = "answer.webm"
    return {
        "audio_bytes": audio_bytes,
        "filename": filename,
        "mime_type": str(value.get("mime_type") or "audio/webm"),
        "duration_seconds": float(value.get("duration_seconds") or 0.0),
        "rms": float(value.get("rms") or 0.0),
        "peak": float(value.get("peak") or 0.0),
        "average_rms": float(value.get("average_rms") or 0.0),
        "active_ratio": float(value.get("active_ratio") or 0.0),
        "track_label": str(value.get("track_label") or ""),
        "track_ready_state": str(value.get("track_ready_state") or ""),
        "track_muted": bool(value.get("track_muted", False)),
        "device_id": str(value.get("device_id") or ""),
        "audio_mode": str(value.get("audio_mode") or audio_mode or "auto"),
        "processing": value.get("processing") if isinstance(value.get("processing"), dict) else {},
    }


def audio_signal_stats(audio_bytes: bytes) -> dict:
    """Inspect a browser WAV recording without storing or returning its audio.

    The browser widget normally returns a 16 kHz PCM WAV.  The signal check
    lets the UI distinguish an actually silent microphone from an STT failure.
    Invalid/non-WAV input is left to the API because some browser versions can
    still produce a valid upload with a slightly different container.
    """
    stats = {
        "parseable": False,
        "duration_seconds": 0.0,
        "rms": 0.0,
        "peak": 0.0,
        "dbfs": -120.0,
        "is_silent": False,
    }
    if not audio_bytes:
        stats["is_silent"] = True
        return stats

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            frames = wav_file.readframes(frame_count)
        if not frames or sample_width not in (1, 2, 3, 4) or frame_rate <= 0:
            stats["parseable"] = True
            stats["is_silent"] = True
            return stats

        rms, peak = _pcm_signal_levels(frames, sample_width)
        dbfs = 20.0 * math.log10(max(rms, 1e-9))
        stats.update(
            parseable=True,
            duration_seconds=frame_count / frame_rate,
            rms=rms,
            peak=peak,
            dbfs=dbfs,
            # Very quiet room noise should not be sent as a speech attempt.
            is_silent=rms < 0.003 and peak < 0.02,
        )
    except (EOFError, OSError, ValueError, wave.Error):
        # Let the transcription endpoint handle an unusual but valid browser
        # container rather than rejecting it locally.
        return stats
    return stats


def _log_audio_event(
    *,
    model: str,
    audio_bytes: bytes,
    stats: dict,
    started: float,
    status: str,
    text_length: int = 0,
) -> None:
    """Record non-sensitive audio diagnostics for troubleshooting."""
    try:
        log_path = Path(__file__).resolve().parent.parent / "data" / "api_calls.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(
                    {
                        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "operation": "audio_transcription",
                        "model": model,
                        "elapsed_seconds": round(time.perf_counter() - started, 3),
                        "audio_bytes": len(audio_bytes),
                        "audio_status": status,
                        "audio_duration_seconds": round(stats.get("duration_seconds", 0.0), 3),
                        "audio_rms": round(stats.get("rms", 0.0), 6),
                        "audio_peak": round(stats.get("peak", 0.0), 6),
                        "audio_average_rms": round(stats.get("average_rms", 0.0), 6),
                        "audio_active_ratio": round(stats.get("active_ratio", 0.0), 4),
                        "audio_dbfs": round(stats.get("dbfs", -120.0), 2),
                        "audio_mode": stats.get("audio_mode", ""),
                        "track_label": stats.get("track_label", ""),
                        "track_ready_state": stats.get("track_ready_state", ""),
                        "track_muted": stats.get("track_muted", False),
                        "audio_processing": stats.get("processing", {}),
                        "text_length": text_length,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "answer.wav",
    client_stats: Optional[dict] = None,
    language: str = "zh",
) -> str:
    """将浏览器录音转成指定语言的文本。"""
    if not audio_bytes:
        return ""

    started = time.perf_counter()
    safe_filename = Path(filename or "answer.wav").name
    if not safe_filename.lower().endswith((".wav", ".mp3", ".m4a", ".webm", ".mp4", ".ogg")):
        safe_filename = "answer.wav"
    model = os.getenv("SILICONFLOW_STT_MODEL", DEFAULT_STT_MODEL)
    language = "en" if str(language).lower().startswith("en") else "zh"
    stats = audio_signal_stats(audio_bytes)
    # MediaRecorder normally returns WebM, which the WAV parser cannot inspect.
    # Reuse the browser-side level meter for a useful silence check and logging.
    if client_stats:
        try:
            client_rms = max(0.0, float(client_stats.get("rms", 0.0)))
            client_peak = max(0.0, float(client_stats.get("peak", 0.0)))
            client_duration = max(0.0, float(client_stats.get("duration_seconds", 0.0)))
            parsed_rms = max(0.0, float(stats.get("rms", 0.0)))
            parsed_peak = max(0.0, float(stats.get("peak", 0.0)))
            effective_rms = max(parsed_rms, client_rms)
            effective_peak = max(parsed_peak, client_peak)
            stats.update(
                duration_seconds=client_duration or stats.get("duration_seconds", 0.0),
                rms=effective_rms,
                peak=effective_peak,
                dbfs=20.0 * math.log10(max(effective_rms, 1e-9)),
                client_meter=True,
                processing=client_stats.get("processing", {})
                if isinstance(client_stats.get("processing"), dict)
                else {},
                # Keep this conservative: a real voice signal is normally well
                # above this level, while an open-mic silence recording is not.
                active_ratio=max(0.0, min(1.0, float(client_stats.get("active_ratio", 0.0) or 0.0))),
                average_rms=max(0.0, float(client_stats.get("average_rms", 0.0) or 0.0)),
                audio_mode=str(client_stats.get("audio_mode", "") or ""),
                track_label=str(client_stats.get("track_label", "") or ""),
                track_ready_state=str(client_stats.get("track_ready_state", "") or ""),
                track_muted=bool(client_stats.get("track_muted", False)),
                # A few Windows/browser combinations expose a working stream
                # but report zero analyser levels. Do not reject those clips
                # solely on the meter; the payload-density check below catches
                # the genuinely empty WebM files seen in practice.
                is_silent=(
                    effective_rms < 0.0015
                    and effective_peak < 0.01
                    and float(client_stats.get("active_ratio", 0.0) or 0.0) < 0.01
                    and (
                        stats.get("parseable")
                        or len(audio_bytes) < max(4096, int(client_duration * 700))
                    )
                ),
            )
        except (TypeError, ValueError):
            pass
    # WebM/MP4 无法用标准库解析，因此也要信任浏览器音量计的结果；
    # 否则“有时长但全静音”的录音会被送到接口并返回空文本。
    if stats.get("is_silent") and (stats.get("parseable") or stats.get("client_meter")):
        _log_audio_event(
            model=model,
            audio_bytes=audio_bytes,
            stats=stats,
            started=started,
            status="silent",
        )
        raise VoiceCaptureError(
            "没有检测到清晰人声。录音开始时会自动停止播报；"
            "把麦克风靠近嘴部约 30–60 厘米，并确认系统输入音量不是静音；"
            "然后重新录音；录音时间可按回答需要决定。"
        )
    if stats.get("track_muted"):
        _log_audio_event(
            model=model,
            audio_bytes=audio_bytes,
            stats=stats,
            started=started,
            status="track_muted",
        )
        raise VoiceCaptureError(
            "浏览器报告当前麦克风音轨已静音。请在录音控件中选择正确的输入设备，"
            "并检查 Windows 输入音量或麦克风物理静音键后重新录音。"
        )

    suffix = Path(safe_filename).suffix.lower()
    mime_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".mp4": "audio/mp4",
        ".ogg": "audio/ogg",
    }.get(suffix, "audio/wav")

    try:
        response = _get_client().audio.transcriptions.create(
            model=model,
            file=(safe_filename, audio_bytes, mime_type),
            language=language,
            response_format="json",
        )
    except Exception:
        _log_audio_event(
            model=model,
            audio_bytes=audio_bytes,
            stats=stats,
            started=started,
            status="api_error",
        )
        raise
    text = getattr(response, "text", "")
    if not text and isinstance(response, dict):
        text = response.get("text", "")
    text = (text or "").strip()

    # 只记录耗时、大小和音量诊断，不记录录音内容。
    _log_audio_event(
        model=model,
        audio_bytes=audio_bytes,
        stats=stats,
        started=started,
        status="ok" if text else "empty_text",
        text_length=len(text),
    )

    return text
