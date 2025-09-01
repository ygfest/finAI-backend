"""
OpenAI API Models

Pydantic models for request/response validation and serialization.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role of the message sender")
    content: Union[str, List[Dict[str, Any]]] = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional name for the message")

    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['system', 'user', 'assistant', 'tool']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {valid_roles}')
        return v


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions."""
    messages: List[ChatMessage] = Field(..., description="List of messages")
    model: str = Field("gpt-4o", description="Model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-p sampling parameter")
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    stream: bool = Field(False, description="Whether to stream the response")


class EmbeddingRequest(BaseModel):
    """Request model for embeddings."""
    input: Union[str, List[str]] = Field(..., description="Text(s) to embed")
    model: str = Field("text-embedding-3-small", description="Embedding model to use")
    encoding_format: Optional[str] = Field("float", description="Format for embeddings")
    dimensions: Optional[int] = Field(None, description="Number of dimensions")
    user: Optional[str] = Field(None, description="Unique identifier for the user")


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str = Field(..., description="Text description of the image")
    model: str = Field("dall-e-3", description="Image generation model")
    size: str = Field("1024x1024", description="Image size")
    quality: str = Field("standard", description="Image quality")
    n: int = Field(1, ge=1, le=10, description="Number of images to generate")
    style: Optional[str] = Field(None, description="Style of the image")

    @validator('size')
    def validate_size(cls, v):
        valid_sizes = ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]
        if v not in valid_sizes:
            raise ValueError(f'Size must be one of: {valid_sizes}')
        return v

    @validator('quality')
    def validate_quality(cls, v):
        valid_qualities = ["standard", "hd"]
        if v not in valid_qualities:
            raise ValueError(f'Quality must be one of: {valid_qualities}')
        return v

    @validator('style')
    def validate_style(cls, v):
        if v is not None:
            valid_styles = ["vivid", "natural"]
            if v not in valid_styles:
                raise ValueError(f'Style must be one of: {valid_styles}')
        return v


class ModerationRequest(BaseModel):
    """Request model for content moderation."""
    input: Union[str, List[str]] = Field(..., description="Content to moderate")


class ModelInfo(BaseModel):
    """Model information response."""
    id: str = Field(..., description="Model ID")
    object: str = Field(..., description="Object type")
    created: int = Field(..., description="Creation timestamp")
    owned_by: str = Field(..., description="Owner of the model")


class ChatCompletionChoice(BaseModel):
    """Chat completion choice."""
    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Message content")
    finish_reason: Optional[str] = Field(None, description="Reason completion finished")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions."""
    id: str = Field(..., description="Completion ID")
    object: str = Field(..., description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[ChatCompletionChoice] = Field(..., description="Completion choices")
    usage: Dict[str, Any] = Field(..., description="Token usage information")


class EmbeddingData(BaseModel):
    """Embedding data item."""
    object: str = Field(..., description="Object type")
    embedding: List[float] = Field(..., description="Embedding vector")
    index: int = Field(..., description="Embedding index")


class EmbeddingResponse(BaseModel):
    """Response model for embeddings."""
    object: str = Field(..., description="Object type")
    data: List[EmbeddingData] = Field(..., description="Embedding data")
    model: str = Field(..., description="Model used")
    usage: Dict[str, Any] = Field(..., description="Token usage information")


class ImageData(BaseModel):
    """Image generation data."""
    url: Optional[str] = Field(None, description="Image URL")
    revised_prompt: Optional[str] = Field(None, description="Revised prompt")


class ImageResponse(BaseModel):
    """Response model for image generation."""
    created: int = Field(..., description="Creation timestamp")
    data: List[ImageData] = Field(..., description="Generated images")


class ModerationResult(BaseModel):
    """Moderation result."""
    flagged: bool = Field(..., description="Whether content was flagged")
    categories: Dict[str, bool] = Field(..., description="Category flags")
    category_scores: Dict[str, float] = Field(..., description="Category scores")


class ModerationResponse(BaseModel):
    """Response model for content moderation."""
    id: str = Field(..., description="Moderation ID")
    model: str = Field(..., description="Model used")
    results: List[ModerationResult] = Field(..., description="Moderation results")


class APIErrorResponse(BaseModel):
    """Standard API error response."""
    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    type: Optional[str] = Field(None, description="Error type")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: Optional[str] = Field(None, description="Service version")
