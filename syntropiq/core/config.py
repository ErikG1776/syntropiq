"""
Configuration Management for Syntropiq

Centralized configuration with environment variable support.
"""

import os
from typing import Optional
from pydantic import BaseModel


class GovernanceConfig(BaseModel):
    """Governance engine configuration."""
    trust_threshold: float = 0.7
    suppression_threshold: float = 0.75
    max_redemption_cycles: int = 4
    drift_detection_delta: float = 0.1
    asymmetric_reward: float = 0.02  # η
    asymmetric_penalty: float = 0.05  # γ
    routing_mode: str = "deterministic"  # "deterministic" | "competitive"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    db_path: str = "governance_state.db"
    connection_pool_size: int = 5
    enable_wal: bool = True  # Write-Ahead Logging for better concurrency


class ExecutorConfig(BaseModel):
    """Execution layer configuration."""
    default_timeout: int = 30  # seconds
    max_retries: int = 3
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class APIConfig(BaseModel):
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = ["*"]


class SyntropiqConfig(BaseModel):
    """Master configuration for Syntropiq."""
    governance: GovernanceConfig = GovernanceConfig()
    database: DatabaseConfig = DatabaseConfig()
    executor: ExecutorConfig = ExecutorConfig()
    api: APIConfig = APIConfig()

    @classmethod
    def from_env(cls) -> "SyntropiqConfig":
        """Load configuration from environment variables."""
        return cls(
            governance=GovernanceConfig(
                trust_threshold=float(os.getenv("TRUST_THRESHOLD", 0.7)),
                suppression_threshold=float(os.getenv("SUPPRESSION_THRESHOLD", 0.75)),
                max_redemption_cycles=int(os.getenv("MAX_REDEMPTION_CYCLES", 4)),
                drift_detection_delta=float(os.getenv("DRIFT_DETECTION_DELTA", 0.1)),
                routing_mode=os.getenv("ROUTING_MODE", "deterministic"),
            ),
            database=DatabaseConfig(
                db_path=os.getenv("DB_PATH", "governance_state.db"),
            ),
            executor=ExecutorConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            ),
            api=APIConfig(
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", 8000)),
                debug=os.getenv("DEBUG", "false").lower() == "true",
            )
        )