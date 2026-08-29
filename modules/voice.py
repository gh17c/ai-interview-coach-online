"""
语音能力
========
使用浏览器录音，再通过当前配置的 OpenAI 兼容接口进行语音转文字。
默认模型为硅基流动的 Qwen3-ASR-1.7B；面试官语音播报由浏览器 SpeechSynthesis 完成，
因此不需要额外的 TTS API Key。
"""

import base64
import binascii
import io
import os
import json
import time
import math
import re
import struct
import wave
from pathlib import Path
from typing import Optional, Union

from modules.api_client import _get_client


DEFAULT_STT_MODEL = "Qwen/Qwen3-ASR-1.7B"
# SiliconFlow occasionally returns an empty HTTP 503 while a speech model is
# being moved between inference workers.  Keep the original model as the
# first choice for compatibility, but allow a second model to take over in
# the same recording attempt.  The list is configurable in .env so users can
# choose models available to their account.
DEFAULT_STT_FALLBACK_MODELS = (
    "Qwen/Qwen3-ASR-1.7B",
    "XingChenAGI/XingChenASR-V3.2",
)
_AUDIO_RECORDER_COMPONENT = None


# 这些别名用于纠正语音识别中常见的同义写法或近似写法。这里只做
# 高置信度的术语规范化，不对普通中文句子做激进的“智能改写”。
PROFESSIONAL_TERM_ALIASES = {
    "晶界": ("晶界面", "晶粒界面"),
    "奥氏体不锈钢": ("奥氏体钢",),
    "固溶处理": ("固溶热处理",),
    "屈服强度": ("屈服应力",),
    "未熔合缺陷": ("未熔合" ,),
    "匙孔孔隙": ("匙孔气孔", "钥匙孔孔隙"),
    "熔池": ("融池",),
    "陶瓷基复合材料": ("陶瓷基复合", "陶瓷基体复合材料"),
    "断裂韧性": ("断裂韧度",),
    "析出强化": ("沉淀强化",),
    "析出相": ("沉淀相",),
    "氧空位": ("氧缺位",),
    "载流子迁移率": ("载流子的迁移率",),
    "关态电流": ("关断电流", "关闭态电流"),
    "碱激发胶凝材料": ("碱激活胶凝材料",),
    "粒化炉渣": ("粒状炉渣",),
    "抗压强度": ("压缩强度",),
    "多孔氮化硅陶瓷": ("多孔氮化硅",),
    "孔隙率": ("气孔率",),
    "双峰孔结构": ("双模态孔结构",),
    "电解液": ("电解质溶液",),
    "高镍层状氧化物": ("高镍层状材料",),
    "比容量": ("比电容量",),
    "磷酸盐涂层": ("磷酸盐包覆层",),
    "倍率性能": ("倍率特性",),
    "热固性聚合物": ("热固性树脂",),
    "交联网络": ("交联结构",),
    "层间强度": ("层间结合强度",),
    "骨整合": ("骨结合",),
    "成骨样细胞": ("成骨细胞样",),
    "自修复涂层": ("自愈合涂层",),
    "缓蚀剂": ("腐蚀抑制剂",),
    "计算材料设计": ("材料计算设计",),
    "第一性原理计算": ("第一性原理模拟",),
    "相场模型": ("相场法模型",),
    "grain boundary": ("grain boundaries", "grain-boundary", "grain-boundaries"),
    "laser powder bed fusion": ("laser powder-bed fusion",),
    "ceramic-matrix composite": ("ceramic matrix composite", "ceramic-matrix composites"),
    "precipitation strengthening": ("precipitation hardening",),
    "oxide semiconductor": ("oxide semi-conductor",),
    "thin film": ("thin films",),
    "alkali-activated binder": ("alkali activated binder", "alkali-activated binders"),
    "silicon nitride ceramic": ("silicon-nitride ceramic", "silicon nitride ceramics"),
    "lithium-ion battery": ("lithium ion battery", "lithium-ion batteries"),
    "high-nickel layered oxide": ("high nickel layered oxide",),
    "thermoset polymer": ("thermosetting polymer", "thermoset polymers"),
    "self-healing coating": ("self healing coating", "self-healing coatings"),
    "first-principles calculation": ("first principles calculation",),
}


def _normalise_term(term: object) -> str:
    return re.sub(r"\s+", " ", str(term or "").strip())


def _term_pattern(term: str) -> str:
    """Build a boundary-aware pattern for Chinese or English terminology."""
    term = _normalise_term(term)
    if not term:
        return r"(?!x)x"
    if re.search(r"[\u4e00-\u9fff]", term) and not re.search(r"[A-Za-z]", term):
        return re.escape(term)
    pieces = [piece for piece in re.split(r"[\s-]+", term) if piece]
    if len(pieces) == 1:
        body = re.escape(pieces[0])
    else:
        body = r"[\s-]+".join(re.escape(piece) for piece in pieces)
    return rf"(?<![A-Za-z]){body}(?![A-Za-z])"


def _english_inflection_compatible(canonical: str, variant: str) -> bool:
    """Avoid changing a source term's singular/plural form during cleanup."""
    canonical_parts = [part for part in re.split(r"[\s-]+", canonical) if part]
    variant_parts = [part for part in re.split(r"[\s-]+", variant) if part]
    if len(canonical_parts) != len(variant_parts) or not canonical_parts:
        return False
    return canonical_parts[-1].lower().endswith("s") == variant_parts[-1].lower().endswith("s")


def _canonical_output_for_variant(canonical: str, variant: str) -> str:
    """Preserve a plural suffix while normalizing a hyphenated English term."""
    if not re.search(r"[A-Za-z]", canonical):
        return canonical
    canonical_parts = [part for part in re.split(r"[\s-]+", canonical) if part]
    variant_parts = [part for part in re.split(r"[\s-]+", variant) if part]
    if len(canonical_parts) != len(variant_parts) or not canonical_parts:
        return canonical
    canonical_last = canonical_parts[-1]
    variant_last = variant_parts[-1]
    if not canonical_last.lower().endswith("s") and variant_last.lower().endswith("s"):
        if canonical_last.lower().endswith("y"):
            canonical_last = canonical_last[:-1] + "ies"
        else:
            canonical_last = canonical_last + "s"
        canonical_parts[-1] = canonical_last
        return " ".join(canonical_parts)
    return canonical


def _term_specs(term_hints: Optional[list[str]] = None) -> list[tuple[str, tuple[str, ...]]]:
    """Merge built-in aliases with the material-specific terms for this clip."""
    merged: dict[str, set[str]] = {}
    for canonical, aliases in PROFESSIONAL_TERM_ALIASES.items():
        canonical = _normalise_term(canonical)
        if canonical:
            merged.setdefault(canonical, set()).update(
                alias for alias in (_normalise_term(value) for value in aliases) if alias
            )
    for hint in term_hints or []:
        canonical = _normalise_term(hint)
        if not canonical:
            continue
        aliases = merged.setdefault(canonical, set())
        aliases.update(
            variant for variant in (
                canonical.replace("-", " "),
                canonical.replace(" ", "-"),
            ) if variant and variant != canonical
        )
    return [
        (canonical, tuple(sorted(aliases, key=len, reverse=True)))
        for canonical, aliases in merged.items()
    ]


def _remove_filler_words(text: str, language: str) -> tuple[str, list[str]]:
    """Remove standalone hesitation sounds while leaving ordinary words intact."""
    removed: list[str] = []
    patterns = []
    if language == "en":
        patterns.append(re.compile(r"(?i)(?<![A-Za-z])(?:uh+|um+|erm+|er+|hmm+)(?![A-Za-z])"))
    else:
        # Repeated characters (嗯嗯、啊啊、呃嗯) are common ASR spellings. A
        # single filler is also removed because SenseVoice often omits pauses.
        patterns.append(re.compile(r"(?<![A-Za-z])(?:嗯+|呃+|额+|唔+|呣+|啊+|唉+)(?![A-Za-z])"))

    def replace(match: re.Match) -> str:
        removed.append(match.group(0))
        return ""

    for pattern in patterns:
        text = pattern.sub(replace, text)
    return text, removed


def _normalise_professional_terms(
    text: str,
    term_hints: Optional[list[str]] = None,
) -> tuple[str, list[dict], list[str]]:
    corrections: list[dict] = []
    specs = _term_specs(term_hints)
    replacements: list[tuple[str, str]] = []
    for canonical, aliases in specs:
        for alias in aliases:
            if re.search(r"[A-Za-z]", canonical) and not _english_inflection_compatible(canonical, alias):
                # A plural hyphenated form can still be safely converted to
                # spaces (e.g. grain-boundaries -> grain boundaries), while
                # a true singular/plural synonym should be left untouched.
                if _canonical_output_for_variant(canonical, alias) == alias:
                    continue
            replacements.append((alias, canonical))
        # Also normalize English capitalization while keeping Chinese text
        # unchanged. Exact canonical matches are naturally no-ops.
        if re.search(r"[A-Za-z]", canonical):
            replacements.append((canonical, canonical))
    replacements.sort(key=lambda item: len(item[0]), reverse=True)

    for variant, canonical in replacements:
        pattern = re.compile(_term_pattern(variant), re.IGNORECASE if re.search(r"[A-Za-z]", variant) else 0)
        replacement_target = _canonical_output_for_variant(canonical, variant)

        def replace(
            match: re.Match,
            canonical: str = canonical,
            replacement_target: str = replacement_target,
        ) -> str:
            original = match.group(0)
            if original != replacement_target:
                corrections.append({"from": original, "to": replacement_target, "_position": match.start()})
            return replacement_target

        text = pattern.sub(replace, text)

    corrections.sort(key=lambda item: item.get("_position", 0))
    for correction in corrections:
        correction.pop("_position", None)
    recognized: list[str] = []
    for canonical, aliases in specs:
        candidates = (canonical, *aliases)
        for candidate in candidates:
            flags = re.IGNORECASE if re.search(r"[A-Za-z]", candidate) else 0
            if re.search(_term_pattern(candidate), text, flags):
                if canonical not in recognized:
                    recognized.append(canonical)
                break
    return text, corrections, recognized


def clean_transcript(
    text: str,
    language: str = "zh",
    term_hints: Optional[list[str]] = None,
) -> dict:
    """清理 ASR 文本并返回可审阅的处理元数据。

    ``text`` 是接口返回的原始转写；``text`` 字段是提交给面试评价的清理后文本。
    不会调用额外模型，因而不会增加录音后的等待时间。
    """
    raw_text = str(text or "").strip()
    normalized_language = "en" if str(language).lower().startswith("en") else "zh"
    without_fillers, fillers_removed = _remove_filler_words(raw_text, normalized_language)
    normalized, term_corrections, recognized_terms = _normalise_professional_terms(
        without_fillers,
        term_hints=term_hints,
    )
    normalized = re.sub(r"\s+([，。！？、；：:,.!?;])", r"\1", normalized)
    normalized = re.sub(r"([，。！？、；：:,.!?;]){2,}", r"\1", normalized)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized).strip(" \t，。！？、；：:,.!?;")
    return {
        "text": normalized,
        "raw_text": raw_text,
        "fillers_removed": fillers_removed,
        "term_corrections": term_corrections,
        "recognized_terms": recognized_terms,
    }


def build_stt_prompt(term_hints: Optional[list[str]] = None, language: str = "zh") -> str:
    """为支持 prompt 的 OpenAI 兼容 STT 服务生成轻量术语上下文。"""
    terms = []
    for hint in term_hints or []:
        value = _normalise_term(hint)
        if value and value not in terms:
            terms.append(value)
    if not terms:
        return ""
    if str(language).lower().startswith("en"):
        prefix = "Materials-science reading. Preserve these technical terms and their spelling: "
    else:
        prefix = "材料科学语音转写，请优先保留以下专业术语，不要将其改写成同音普通词："
    return prefix + ", ".join(terms[:40])


class VoiceCaptureError(ValueError):
    """The recording cannot be usefully sent to speech recognition."""


class EmptyTranscriptionError(VoiceCaptureError):
    """The provider responded successfully but returned no transcript."""


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
    error_status_code: Optional[int] = None,
    error_type: str = "",
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
                        **({"error_status_code": error_status_code} if error_status_code else {}),
                        **({"error_type": error_type} if error_type else {}),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass


def _prompt_argument_unsupported(error: Exception) -> bool:
    """判断兼容接口是否只是不接受可选的 prompt 参数。"""
    message = str(error or "").lower()
    return "prompt" in message and any(
        marker in message
        for marker in (
            "unknown",
            "unsupported",
            "unexpected",
            "invalid",
            "extra",
            "unrecognized",
            "not allowed",
        )
    )


def _error_status_code(error: Exception) -> Optional[int]:
    """Extract an HTTP status code from OpenAI-compatible client errors."""
    for candidate in (
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        try:
            if candidate is not None:
                return int(candidate)
        except (TypeError, ValueError):
            continue
    match = re.search(r"\b(4\d\d|5\d\d)\b", str(error or ""))
    return int(match.group(1)) if match else None


def _is_retryable_transcription_error(error: Exception) -> bool:
    """Return True for transient provider/network failures."""
    status_code = _error_status_code(error)
    if status_code in {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524}:
        return True
    return isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {
        "APITimeoutError",
        "APIConnectionError",
    }


def _stt_retry_limit() -> int:
    try:
        return max(0, min(4, int(os.getenv("SILICONFLOW_STT_MAX_RETRIES", "3"))))
    except (TypeError, ValueError):
        return 3


def _stt_timeout_seconds() -> float:
    """Return a bounded per-request timeout for the interactive STT call.

    The OpenAI client default is several minutes.  That is a poor fit for a
    Streamlit interaction: a stalled 503/connection can otherwise leave the
    page spinning for 10+ minutes before the retry/failover code gets a chance
    to run.  Keep the value configurable for longer recordings, but never
    allow an accidental zero or an unbounded value.
    """
    try:
        return max(10.0, min(180.0, float(os.getenv("SILICONFLOW_STT_TIMEOUT_SECONDS", "90"))))
    except (TypeError, ValueError):
        return 90.0


def _stt_model_candidates(primary_model: Optional[str] = None) -> list[str]:
    """Return the primary STT model followed by unique configured fallbacks.

    SiliconFlow model availability can vary by account and region.  Reading
    this setting for every recording (rather than at import time) also makes
    it possible to change ``.env`` and restart only the Streamlit process.
    Set ``SILICONFLOW_STT_FALLBACK_MODELS=`` to disable failover explicitly.
    """
    primary = str(
        primary_model
        or os.getenv("SILICONFLOW_STT_MODEL", DEFAULT_STT_MODEL)
        or DEFAULT_STT_MODEL
    ).strip()
    configured = os.getenv("SILICONFLOW_STT_FALLBACK_MODELS")
    if configured is None:
        fallback_values = list(DEFAULT_STT_FALLBACK_MODELS)
    else:
        fallback_values = re.split(r"[,;\n]", configured)
    candidates: list[str] = []
    for value in [primary, *fallback_values]:
        model = str(value or "").strip()
        if model and model not in candidates:
            candidates.append(model)
    return candidates or [DEFAULT_STT_MODEL]


def _create_transcription_with_retry(client, request_kwargs: dict):
    """Call the STT endpoint with bounded retry/backoff for transient errors."""
    retry_limit = _stt_retry_limit()
    timeout_seconds = _stt_timeout_seconds()
    last_error = None
    for attempt in range(retry_limit + 1):
        try:
            timed_kwargs = dict(request_kwargs)
            timed_kwargs.setdefault("timeout", timeout_seconds)
            try:
                return client.audio.transcriptions.create(**timed_kwargs)
            except TypeError as exc:
                # Very old OpenAI-compatible client wrappers may not expose
                # the per-call timeout keyword.  Retain compatibility for
                # those wrappers; current OpenAI clients always take the
                # bounded path above.
                message = str(exc or "").lower()
                if "timeout" not in message or not any(
                    marker in message
                    for marker in ("unexpected", "unknown", "unsupported", "invalid", "keyword")
                ):
                    raise
                return client.audio.transcriptions.create(**request_kwargs)
        except Exception as exc:
            last_error = exc
            if not _is_retryable_transcription_error(exc) or attempt >= retry_limit:
                raise
            # Keep waits short enough for an interactive interview while
            # avoiding a burst against a temporarily unavailable endpoint.
            delay = min(4.0, 0.6 * (2 ** attempt))
            time.sleep(delay)
    raise last_error


def _transcription_text(response: object) -> str:
    """Extract text from SDK objects and dict responses consistently."""
    text = getattr(response, "text", "")
    if not text and isinstance(response, dict):
        text = response.get("text", "")
    return str(text or "").strip()


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "answer.wav",
    client_stats: Optional[dict] = None,
    language: str = "zh",
    term_hints: Optional[list[str]] = None,
    return_metadata: bool = False,
) -> Union[str, dict]:
    """将浏览器录音转成指定语言的文本，并清理停顿词与材料术语。

    默认返回清理后的字符串以兼容旧调用；设置 ``return_metadata=True``
    时返回 ``clean_transcript`` 的完整结果，便于界面展示原始转写和处理摘要。
    """
    if not audio_bytes:
        return ""

    started = time.perf_counter()
    safe_filename = Path(filename or "answer.wav").name
    if not safe_filename.lower().endswith((".wav", ".mp3", ".m4a", ".webm", ".mp4", ".ogg")):
        safe_filename = "answer.wav"
    model_candidates = _stt_model_candidates()
    model = model_candidates[0]
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

    request_kwargs = {
        "file": (safe_filename, audio_bytes, mime_type),
        "language": language,
        "response_format": "json",
    }
    stt_prompt = build_stt_prompt(term_hints=term_hints, language=language)
    if stt_prompt:
        # OpenAI-compatible providers that support prompt can use this as a
        # lightweight hotword hint. A compatibility fallback below keeps
        # older SiliconFlow deployments working if they reject the field.
        request_kwargs["prompt"] = stt_prompt

    response = None
    used_model = model
    last_error: Optional[Exception] = None
    attempted_models: list[str] = []
    empty_models: list[str] = []
    try:
        client = _get_client()
        for candidate_model in model_candidates:
            attempted_models.append(candidate_model)
            candidate_kwargs = dict(request_kwargs)
            candidate_kwargs["model"] = candidate_model
            try:
                try:
                    response = _create_transcription_with_retry(client, candidate_kwargs)
                except Exception as exc:
                    # Some OpenAI-compatible gateways reject the optional
                    # prompt field.  Retry this same model once without the
                    # hint before considering it unavailable.
                    if "prompt" in candidate_kwargs and _prompt_argument_unsupported(exc):
                        candidate_kwargs.pop("prompt", None)
                        response = _create_transcription_with_retry(client, candidate_kwargs)
                    else:
                        raise
                candidate_response = response
                response_text = _transcription_text(candidate_response)
                # A successful HTTP response with an empty ``text`` is a
                # common failure mode for an overloaded/incorrectly routed
                # ASR worker.  Give the next configured model a chance instead
                # of returning an empty transcript immediately.
                if response_text:
                    response = candidate_response
                    used_model = candidate_model
                    break
                response = None
                used_model = candidate_model
                empty_models.append(candidate_model)
                last_error = RuntimeError(f"语音模型 {candidate_model} 返回空文本")
                continue
            except Exception as exc:
                last_error = exc
                response = None
                # A fallback model is useful only for transient provider
                # failures.  Preserve validation/authentication errors so the
                # caller receives the real configuration problem.
                if not _is_retryable_transcription_error(exc):
                    raise
                continue
        if response is None and last_error is not None:
            if empty_models and str(last_error).startswith("语音模型 "):
                models_label = "、".join(empty_models)
                raise EmptyTranscriptionError(
                    f"语音识别服务返回空文本（已尝试：{models_label}）。"
                    "请确认录音音量条有变化，或点击“重试此录音”再试一次。"
                )
            raise last_error
        if response is None:
            raise RuntimeError("语音识别没有返回响应")
    except Exception as exc:
        _log_audio_event(
            model=used_model,
            audio_bytes=audio_bytes,
            stats=stats,
            started=started,
            status="empty_text" if isinstance(exc, EmptyTranscriptionError) else "api_error",
            error_status_code=_error_status_code(exc),
            error_type="EmptyTranscription" if isinstance(exc, EmptyTranscriptionError) else type(exc).__name__,
        )
        status_code = _error_status_code(exc)
        if status_code in {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524}:
            models_label = "、".join(attempted_models) or model
            raise VoiceCaptureError(
                f"语音识别服务暂时不可用（HTTP {status_code}）。已自动重试 {_stt_retry_limit()} 次，"
                f"并尝试备用模型（{models_label}）。请稍等片刻后重新录音；"
                "如果持续出现，请在硅基流动控制台检查模型状态、额度和网络连接。"
            ) from exc
        raise
    text = _transcription_text(response)
    cleaned = clean_transcript(text, language=language, term_hints=term_hints)
    text = cleaned["text"]

    # 只记录耗时、大小和音量诊断，不记录录音内容。
    _log_audio_event(
        model=used_model,
        audio_bytes=audio_bytes,
        stats=stats,
        started=started,
        status="ok" if text else "empty_text",
        text_length=len(text),
    )

    return cleaned if return_metadata else text
