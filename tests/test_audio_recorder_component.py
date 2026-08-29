from pathlib import Path
import unittest


COMPONENT_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "audio_recorder"
    / "index.html"
)


class AudioRecorderComponentTests(unittest.TestCase):
    def test_recorder_requests_open_microphone_constraints(self):
        source = COMPONENT_SOURCE.read_text(encoding="utf-8")

        self.assertIn("navigator.mediaDevices.getUserMedia", source)
        self.assertIn("echoCancellation: false", source)
        self.assertIn("noiseSuppression: false", source)
        self.assertIn("autoGainControl: false", source)
        self.assertIn("channelCount", source)
        self.assertIn("sampleRate", source)
        self.assertIn("getSettings", source)
        self.assertIn("processing", source)
        self.assertIn("deviceSelect", source)
        self.assertIn("modeSelect", source)
        self.assertIn("devicechange", source)
        self.assertIn("Microphone track is muted or inactive", source)
        self.assertIn("deviceIds.forEach", source)
        self.assertIn("activeSettings.deviceId", source)
        self.assertIn("waitForUsableTrack", source)
        self.assertIn('track.addEventListener("unmute"', source)
        self.assertIn('activeTrack.addEventListener("mute"', source)
        self.assertIn("active_ratio", source)
        self.assertIn("convertToWav", source)
        self.assertIn("decodeAudioData", source)
        self.assertIn('audio/wav', source)


    def test_recorder_stops_speech_before_recording_and_returns_component_value(self):
        source = COMPONENT_SOURCE.read_text(encoding="utf-8")

        self.assertIn("speechSynthesis.cancel()", source)
        self.assertIn("streamlit:componentReady", source)
        self.assertIn("streamlit:setComponentValue", source)
        self.assertIn("audio_base64", source)

    def test_recorder_uses_long_safety_limit_and_manual_stop(self):
        source = COMPONENT_SOURCE.read_text(encoding="utf-8")

        self.assertIn("let maxSeconds = 600", source)
        self.assertIn("Math.min(600", source)
        self.assertIn("mediaRecorder.stop()", source)
        self.assertIn("最长还可录", source)
