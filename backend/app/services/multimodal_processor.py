import base64
import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from pydantic import BaseModel

class MediaType(Enum):
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"
    MULTIMODAL = "multimodal"

@dataclass
class AudioSegment:
    id: str
    data: bytes
    format: str  # wav, mp3, opus, etc.
    duration_ms: int
    sample_rate: int
    channels: int
    metadata: Dict[str, Any] = None

@dataclass
class VideoFrame:
    id: str
    frame_data: bytes
    width: int
    height: int
    timestamp_ms: int
    format: str  # jpeg, png, h264, etc.
    metadata: Dict[str, Any] = None

@dataclass
class MediaMessage:
    id: str
    role: str
    media_type: MediaType
    content: Optional[str] = None  # Text content for multimodal messages
    audio_segments: Optional[List[AudioSegment]] = None
    video_frames: Optional[List[VideoFrame]] = None
    metadata: Dict[str, Any] = None
    timestamp: Optional[int] = None

class MultimodalProcessor:
    """Process native audio and video messages for multimodal LLM models"""
    
    def __init__(self):
        self.supported_audio_formats = ["wav", "mp3", "opus", "flac", "aac"]
        self.supported_video_formats = ["jpeg", "png", "h264", "mp4"]
    
    async def process_multimodal_messages(
        self, 
        messages: List[Dict[str, Any]],
        provider: str
    ) -> List[Dict[str, Any]]:
        """Convert messages to multimodal format for specific LLM provider"""
        
        # Convert text messages to format expected by multimodal models
        processed_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            
            # Check if this contains native media data
            has_media = (
                msg.get("audio_segments") or 
                msg.get("video_frames") or
                msg.get("audio_data") or
                msg.get("video_data")
            )
            
            if has_media:
                # Create multimodal message for vision/audio models
                processed_msg = {
                    "role": role,
                    "content": [{"type": "text", "text": raw_content}] if raw_content else []
                }
                
                # Add audio segments if present
                if msg.get("audio_data"):
                    audio_segments = msg["audio_data"]
                    if isinstance(audio_segments, str):
                        # Base64 encoded audio
                        processed_msg["content"].append({
                            "type": "audio",
                            "audio": audio_segments,
                            "mime_type": "audio/wav"
                        })
                    elif isinstance(audio_segments, bytes):
                        processed_msg["content"].append({
                            "type": "audio",
                            "audio": base64.b64encode(audio_segments).decode("utf-8"),
                            "mime_type": "audio/wav"
                        })
                
                # Add video frames if present
                if msg.get("video_data"):
                    video_frames = msg["video_data"]
                    if isinstance(video_frames, list):
                        for frame_data in video_frames[:3]:  # Limit to first 3 frames
                            if frame_data:
                                processed_msg["content"].append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64.b64encode(frame_data).decode('utf-8')}"
                                    }
                                })
                    elif isinstance(video_frames, bytes):
                        processed_msg["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64.b64encode(video_frames).decode('utf-8')}"
                            }
                        })
                
                processed_messages.append(processed_msg)
            else:
                # Regular text message
                processed_messages.append({
                    "role": role,
                    "content": raw_content
                })
        
        return processed_messages
    
    async def extract_media_from_message(self, message: Dict[str, Any]) -> Optional[MediaMessage]:
        """Extract media information from a message"""
        
        # Determine media type
        media_type = MediaType.TEXT
        has_audio = False
        has_video = False
        
        # Check for audio indicators
        if (
            message.get("audio_data") or
            message.get("audio_segments") or
            message.get("audio_url") or
            message.get("audio_file")
        ):
            has_audio = True
        
        # Check for video indicators  
        if (
            message.get("video_data") or
            message.get("video_frames") or
            message.get("video_url") or
            message.get("video_file") or
            message.get("image_data") or
            message.get("screenshot")
        ):
            has_video = True
        
        if has_audio and has_video:
            media_type = MediaType.MULTIMODAL
        elif has_audio:
            media_type = MediaType.AUDIO
        elif has_video:
            media_type = MediaType.VIDEO
        
        if media_type == MediaType.TEXT:
            return None
        
        # Extract message ID and role
        msg_id = message.get("id", f"msg-{hash(str(message)) % 10000}")
        role = message.get("role", "user")
        
        # Create MediaMessage
        return MediaMessage(
            id=msg_id,
            role=role,
            media_type=media_type,
            content=message.get("content"),
            audio_segments=[
                AudioSegment(
                    id=f"audio-{i}",
                    data=message["audio_data"] if isinstance(message.get("audio_data"), bytes) else base64.b64decode(message["audio_data"]),
                    format=message.get("audio_format", "wav"),
                    duration_ms=message.get("audio_duration_ms", 0),
                    sample_rate=message.get("audio_sample_rate", 16000)
                )
            ] if has_audio else None,
            video_frames=[
                VideoFrame(
                    id=f"frame-{i}",
                    frame_data=message["video_data"] if isinstance(message.get("video_data"), bytes) else base64.b64decode(message["video_data"]),
                    width=message.get("video_width", 640),
                    height=message.get("video_height", 480),
                    timestamp_ms=i * 1000,
                    format=message.get("video_format", "jpeg")
                )
                for i in range(len(message.get("video_data", [])) if isinstance(message.get("video_data"), list) else 1)
            ] if has_video else None,
            metadata={
                "source": message.get("source"),
                "format": message.get("format"),
                "duration_ms": message.get("duration_ms"),
                "timestamp": message.get("timestamp")
            }
        )
    
    async def create_multimodal_prompt(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        provider: str = "openai-compatible"
    ) -> List[Dict[str, Any]]:
        """Create a multimodal prompt for the given LLM provider"""
        
        # Extract and process media messages
        media_messages = []
        text_messages = []
        
        for msg in messages:
            media_msg = await self.extract_media_from_message(msg)
            if media_msg:
                media_messages.append(media_msg)
            else:
                text_messages.append(msg)
        
        # Combine text messages with system prompt if present
        prompt = []
        if system_prompt:
            prompt.append({"role": "system", "content": system_prompt})
        
        # Add text messages
        prompt.extend(text_messages)
        
        # For certain providers, combine media with text
        if provider == "openai-compatible" and media_messages:
            # Merge the first text message with media if possible
            if prompt:
                merged_content = []
                if prompt[0]["role"] == "user":
                    # Add text content to the prompt
                    pass  # Keep as-is for now
                
                # Add media content to the last message
                last_msg = prompt[-1]
                if last_msg["role"] == "user":
                    last_msg["content"] = last_msg.get("content", "")
        
        return prompt

# Singleton instance
multimodal_processor = MultimodalProcessor()
