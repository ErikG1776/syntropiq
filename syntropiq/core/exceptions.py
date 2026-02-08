"""
Custom Exceptions for Syntropiq

Provides specific exception types for different failure modes.
"""


class SyntropiqError(Exception):
    """Base exception for all Syntropiq errors."""
    pass


class CircuitBreakerTriggered(SyntropiqError):
    """
    Raised when circuit breaker halts execution.
    
    Occurs when no agents meet the trust threshold.
    Patent Claim 2: Circuit-breaker pattern.
    """
    pass


class NoAgentsAvailable(SyntropiqError):
    """Raised when no agents are registered in the system."""
    pass


class AgentExecutionError(SyntropiqError):
    """Raised when an agent fails to execute a task."""
    pass


class InvalidConfiguration(SyntropiqError):
    """Raised when configuration is invalid or missing required values."""
    pass


class DatabaseError(SyntropiqError):
    """Raised when database operations fail."""
    pass


class TrustScoreInvalid(SyntropiqError):
    """Raised when trust score is out of valid range [0.0, 1.0]."""
    pass


class SuppressionError(SyntropiqError):
    """Raised when suppression/redemption cycle operations fail."""
    pass