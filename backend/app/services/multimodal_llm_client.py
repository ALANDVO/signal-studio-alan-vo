import asyncio
from typing import List, Dict, Any, Optional
from .llm_client import dispatch_llm_request, LLMResult
from .multimodal_processor import multimodal_processor

async def process_multimodal_content(
    messages: List[Dict[str, Any]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> LLMResult:
    """
    Process multimodal content (audio/video) before sending to LLM.
    
    This function handles native audio and video streaming without mandatory STT transcription,
    enabling direct multimodal support for vision and speech models.
    """
    
    # Extract audio/video messages and process them
    media_messages = []
    text_messages = []
    
    for msg in messages:
        # Check if this message contains native media data
        has_media = (
            msg.get("audio_data") or
            msg.get("video_data") or
            msg.get("audio_segments") or
            msg.get("video_frames") or
            msg.get("audio_url") or
            msg.get("video_url") or
            msg.get("audio_file") or
            msg.get("video_file") or
            msg.get("image_data") or
            msg.get("screenshot")
        )
        
        if has_media:
            media_messages.append(msg)
        else:
            text_messages.append(msg)
    
    # Process multimodal messages
    if media_messages:
        # Combine with text messages for processing
        all_messages = text_messages + media_messages
        
        # Use multimodal processor to handle the content
        try:
            processed_messages = await multimodal_processor.process_multimodal_messages(
                all_messages, 
                provider or "openai-compatible"
            )
            
            # For now, send to existing LLM client for backward compatibility
            # In a real implementation, this would use provider-specific multimodal APIs
            return await dispatch_llm_request(
                processed_messages,
                provider=provider,
                model=model,
                system_prompt=system_prompt
            )
        except Exception as e:
            # Fallback to text-only processing if multimodal processing fails
            print(f"Multimodal processing failed, falling back to text-only: {e}")
            return await dispatch_llm_request(
                text_messages,
                provider=provider,
                model=model,
                system_prompt=system_prompt
            )
    
    # If no media messages, use original text-only processing
    return await dispatch_llm_request(
        messages,
        provider=provider,
        model=model,
        system_prompt=system_prompt
    )

async def create_multimodal_prompt(
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    provider: str = "openai-compatible"
) -> List[Dict[str, Any]]:
    """Create a multimodal prompt for the given LLM provider"""
    return await multimodal_processor.create_multimodal_prompt(
        messages, system_prompt, provider
    )
