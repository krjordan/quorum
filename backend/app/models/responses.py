"""
Response models - Standard API response schemas
"""
from pydantic import BaseModel
from typing import List, Optional


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    openai_configured: bool


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    provider: str
    streaming: bool = True


class ModelsResponse(BaseModel):
    """Available models response"""
    models: List[ModelInfo]


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None
