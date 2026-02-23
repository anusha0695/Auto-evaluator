"""Configuration management for the evaluation framework"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""
    
    # GCP Project
    gcp_project_id: str
    
    # Document AI Configuration
    document_ai_processor_id: str
    document_ai_location: str = "us"
    
    # Vertex AI Configuration
    vertex_ai_location: str = "us-central1"
    gemini_model: str = "gemini-1.5-flash-002"
    gemini_temperature: float = 0.0
    gemini_max_tokens: int = 8192
    
    # Prompts
    prompt_dir: str = "Prompts/raw_text"
    primary_prompt_file: str = "primary_classifier_agent_prompt.txt"
    
    # Default paths for testing (can be overridden by command line)
    default_input_pdf: str = "data/input/raw_documents/doc2_1.pdf"
    default_output_dir: str = "output"
    default_output_file: str = "classification_result.json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
