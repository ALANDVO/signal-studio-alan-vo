"""Tests for the multimodal processor - direct audio/video streaming to LLM models."""

import pytest
import base64
from backend.app.services.multimodal_processor import (
    MultimodalProcessor,
    MediaType,
    AudioSegment,
    VideoFrame,
    MediaMessage,
)


@pytest.fixture
def processor():
    return MultimodalProcessor()


class TestExtractMediaFromMessage:
    """Test extract_media_from_message method."""

    @pytest.mark.asyncio
    async def test_extract_audio_message(self, processor):
        """Test extracting audio from a message with audio_data."""
        msg = {
            "id": "msg1",
            "role": "user",
            "content": "Look at this",
            "audio_data": b"\x00\x01\x02\x03",
            "audio_format": "wav",
            "audio_sample_rate": 16000,
            "audio_channels": 1,
            "audio_duration_ms": 1000,
        }
        result = await processor.extract_media_from_message(msg)
        assert result is not None
        assert result.media_type == MediaType.AUDIO
        assert result.audio_segments is not None
        assert len(result.audio_segments) == 1
        assert result.audio_segments[0].format == "wav"
        assert result.audio_segments[0].sample_rate == 16000
        assert result.audio_segments[0].channels == 1

    @pytest.mark.asyncio
    async def test_extract_video_message_single_frame(self, processor):
        """Test extracting video from a message with single video_data byte."""
        msg = {
            "id": "msg2",
            "role": "user",
            "content": "Look at this",
            "video_data": b"\x00\x01\x02\x03",
            "video_format": "jpeg",
            "video_width": 640,
            "video_height": 480,
        }
        result = await processor.extract_media_from_message(msg)
        assert result is not None
        assert result.media_type == MediaType.VIDEO
        assert result.video_frames is not None
        assert len(result.video_frames) == 1
        assert result.video_frames[0].width == 640
        assert result.video_frames[0].height == 480

    @pytest.mark.asyncio
    async def test_extract_video_message_multiple_frames(self, processor):
        """Test extracting video from a message with list video_data."""
        msg = {
            "id": "msg3",
            "role": "user",
            "content": "Look at this",
            "video_data": [b"frame1", b"frame2", b"frame3"],
            "video_format": "jpeg",
            "video_width": 640,
            "video_height": 480,
        }
        result = await processor.extract_media_from_message(msg)
        assert result is not None
        assert result.media_type == MediaType.VIDEO
        assert result.video_frames is not None
        assert len(result.video_frames) == 3
        assert result.video_frames[0].timestamp_ms == 0
        assert result.video_frames[1].timestamp_ms == 1000
        assert result.video_frames[2].timestamp_ms == 2000

    @pytest.mark.asyncio
    async def test_extract_text_only_message(self, processor):
        """Test that text-only messages return None."""
        msg = {"id": "msg4", "role": "user", "content": "Just text"}
        result = await processor.extract_media_from_message(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_multimodal_message(self, processor):
        """Test extracting both audio and video."""
        msg = {
            "id": "msg5",
            "role": "user",
            "content": "Look and listen",
            "audio_data": b"\x00\x01",
            "audio_format": "wav",
            "audio_sample_rate": 8000,
            "audio_channels": 2,
            "video_data": b"\x00\x01\x02",
            "video_format": "jpeg",
            "video_width": 320,
            "video_height": 240,
        }
        result = await processor.extract_media_from_message(msg)
        assert result is not None
        assert result.media_type == MediaType.MULTIMODAL
        assert result.audio_segments is not None
        assert result.video_frames is not None


class TestProcessMultimodalMessages:
    """Test process_multimodal_messages method."""

    @pytest.mark.asyncio
    async def test_process_audio_message(self, processor):
        """Test processing a message with audio data."""
        messages = [
            {"role": "user", "content": "Hello", "audio_data": b"test audio data"},
        ]
        processed = await processor.process_multimodal_messages(messages, "openai-compatible")
        assert len(processed) == 1
        assert processed[0]["role"] == "user"
        assert isinstance(processed[0]["content"], list)
        assert {"type": "text", "text": "Hello"} in processed[0]["content"]
        # Check audio is present (may have additional keys like mime_type)
        audio_items = [item for item in processed[0]["content"] if item.get("type") == "audio"]
        assert len(audio_items) >= 1
        assert audio_items[0].get("mime_type") == "audio/wav"

    @pytest.mark.asyncio
    async def test_process_video_message(self, processor):
        """Test processing a message with video data."""
        messages = [
            {"role": "user", "content": "Look at this", "video_data": b"test video data"},
        ]
        processed = await processor.process_multimodal_messages(messages, "openai-compatible")
        assert len(processed) == 1
        assert processed[0]["role"] == "user"
        assert isinstance(processed[0]["content"], list)
        assert {"type": "text", "text": "Look at this"} in processed[0]["content"]
        # Check video is present
        video_items = [item for item in processed[0]["content"] if item.get("type") == "image_url"]
        assert len(video_items) >= 1

    @pytest.mark.asyncio
    async def test_process_mixed_messages(self, processor):
        """Test processing mixed audio and video messages."""
        messages = [
            {"role": "user", "content": "Hello", "audio_data": b"test audio"},
            {"role": "user", "content": "Look", "video_data": b"test video"},
        ]
        processed = await processor.process_multimodal_messages(messages, "openai-compatible")
        assert len(processed) == 2
        # First message should have audio
        audio_items = [item for item in processed[0]["content"] if item.get("type") == "audio"]
        assert len(audio_items) >= 1
        # Second message should have video
        video_items = [item for item in processed[1]["content"] if item.get("type") == "image_url"]
        assert len(video_items) >= 1

    @pytest.mark.asyncio
    async def test_process_text_only_message(self, processor):
        """Test processing a text-only message."""
        messages = [
            {"role": "user", "content": "Just text, no media"},
        ]
        processed = await processor.process_multimodal_messages(messages, "openai-compatible")
        assert len(processed) == 1
        assert processed[0]["role"] == "user"
        assert processed[0]["content"] == "Just text, no media"


class TestCreateMultimodalPrompt:
    """Test create_multimodal_prompt method."""

    @pytest.mark.asyncio
    async def test_create_prompt_with_audio(self, processor):
        """Test creating a multimodal prompt with audio."""
        messages = [
            {"role": "user", "content": "Hello", "audio_data": b"test audio"},
        ]
        prompt = await processor.create_multimodal_prompt(messages, "You are helpful", "openai-compatible")
        assert len(prompt) == 1
        assert prompt[0]["role"] == "user"
        assert isinstance(prompt[0]["content"], list)
        assert {"type": "text", "text": "Hello"} in prompt[0]["content"]
        expected_audio = {"type": "audio", "audio": base64.b64encode(b"test audio").decode("utf-8"), "mime_type": "audio/wav"}
        assert expected_audio in prompt[0]["content"]

    @pytest.mark.asyncio
    async def test_create_prompt_with_video(self, processor):
        """Test creating a multimodal prompt with video."""
        messages = [
            {"role": "user", "content": "Look at this", "video_data": b"test video"},
        ]
        prompt = await processor.create_multimodal_prompt(messages, "You are helpful", "openai-compatible")
        assert len(prompt) == 1
        assert prompt[0]["role"] == "user"
        assert isinstance(prompt[0]["content"], list)
        assert {"type": "text", "text": "Look at this"} in prompt[0]["content"]
        encoded = base64.b64encode(b"test video").decode("utf-8")
        expected_video = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
        assert expected_video in prompt[0]["content"]

    @pytest.mark.asyncio
    async def test_create_prompt_mixed_audio_video(self, processor):
        """Test creating a multimodal prompt with both audio and video."""
        messages = [
            {"role": "user", "content": "Hello", "audio_data": b"test audio"},
            {"role": "user", "content": "Look", "video_data": b"test video"},
        ]
        prompt = await processor.create_multimodal_prompt(messages, "You are helpful", "openai-compatible")
        assert len(prompt) == 2
        # First message should have audio
        expected_audio = {"type": "audio", "audio": base64.b64encode(b"test audio").decode("utf-8"), "mime_type": "audio/wav"}
        assert expected_audio in prompt[0]["content"]
        # Second message should have video
        encoded = base64.b64encode(b"test video").decode("utf-8")
        expected_video = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
        assert expected_video in prompt[1]["content"]

    @pytest.mark.asyncio
    async def test_create_prompt_text_only(self, processor):
        """Test creating a multimodal prompt with text only."""
        messages = [
            {"role": "user", "content": "Just text"},
        ]
        prompt = await processor.create_multimodal_prompt(messages, "You are helpful", "openai-compatible")
        assert len(prompt) == 1
        assert prompt[0]["role"] == "user"
        assert prompt[0]["content"] == "Just text"


class TestMediaMessageDataclass:
    """Test MediaMessage dataclass construction."""

    @pytest.mark.asyncio
    async def test_media_message_with_audio(self, processor):
        """Test MediaMessage with audio segments."""
        msg = {
            "id": "msg1",
            "role": "user",
            "content": "Listen to this",
            "audio_data": b"\x00\x01\x02\x03",
            "audio_format": "wav",
            "audio_sample_rate": 16000,
            "audio_channels": 1,
            "audio_duration_ms": 500,
        }
        result = await processor.extract_media_from_message(msg)
        assert result is not None
        assert result.media_type == MediaType.AUDIO
        assert result.content == "Listen to this"
        assert result.audio_segments is not None
        assert len(result.audio_segments) == 1
        seg = result.audio_segments[0]
        assert seg.id.startswith("audio-")
        assert seg.format == "wav"
        assert seg.sample_rate == 16000
        assert seg.channels == 1
        assert seg.duration_ms == 500

    @pytest.mark.asyncio
    async def test_media_message_with_video(self, processor):
        """Test MediaMessage with video frames."""
        msg = {
            "id": "msg2",
            "role": "user",
            "content": "Watch this",
            "video_data": [b"frame1", b"frame2"],
            "video_format": "jpeg",
            "video_width": 640,
            "video_height": 480,
        }
        result = await processor.extract_media_from_message(msg)
        assert result is not None
        assert result.media_type == MediaType.VIDEO
        assert result.content == "Watch this"
        assert result.video_frames is not None
        assert len(result.video_frames) == 2
        for i, frame in enumerate(result.video_frames):
            assert frame.id.startswith("frame-")
            assert frame.width == 640
            assert frame.height == 480
            assert frame.timestamp_ms == i * 1000


class TestMediaTypeEnum:
    """Test MediaType enum values."""

    def test_media_type_values(self):
        """Test that MediaType enum has correct values."""
        assert MediaType.AUDIO.value == "audio"
        assert MediaType.VIDEO.value == "video"
        assert MediaType.TEXT.value == "text"
        assert MediaType.MULTIMODAL.value == "multimodal"
