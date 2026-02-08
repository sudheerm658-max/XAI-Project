"""
Unit tests for core modules.
"""

import pytest
from src.grok_insights.core.settings import Settings
from src.grok_insights.worker.grok_client import analyze


@pytest.mark.unit
def test_settings_defaults():
    """Test default settings."""
    settings = Settings()
    assert settings.APP_NAME == "Grok Insights Backend"
    assert settings.GROK_MODE == "mock"
    assert settings.MAX_BATCH_SIZE == 50
    assert settings.RATE_LIMIT_REQUESTS == 60


@pytest.mark.unit
def test_settings_environment_override(monkeypatch):
    """Test settings override from environment."""
    monkeypatch.setenv("GROK_MODE", "real")
    monkeypatch.setenv("MAX_BATCH_SIZE", "100")
    
    settings = Settings()
    assert settings.GROK_MODE == "real"
    assert settings.MAX_BATCH_SIZE == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_analyze():
    """Test mock Grok analysis."""
    text = "This is a great service! Thanks for the support."
    result = await analyze(text)
    
    assert result["summary"] is not None
    assert result["sentiment"] in ["positive", "negative", "neutral"]
    assert isinstance(result["topics"], list)
    assert "meta" in result
    assert result["meta"]["mock"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_sentiment_positive():
    """Test positive sentiment detection."""
    text = "I love this product! Excellent service."
    result = await analyze(text)
    assert result["sentiment"] == "positive"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_sentiment_negative():
    """Test negative sentiment detection."""
    text = "This is terrible! Worst experience ever."
    result = await analyze(text)
    assert result["sentiment"] == "negative"


@pytest.mark.unit
def test_settings_is_production():
    """Test environment detection."""
    settings = Settings(ENVIRONMENT="production")
    assert settings.is_production is True
    assert settings.is_development is False


@pytest.mark.unit
def test_settings_database_url_postgres():
    """Test PostgreSQL database detection."""
    settings = Settings(DATABASE_URL="postgresql://user:pass@localhost/db")
    assert settings.database_is_sqlite is False
