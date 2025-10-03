"""
Signal data models
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class SignalStatus(str, Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    STOPPED = "stopped"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"

class TimeFrame(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class AnalysisMethod(str, Enum):
    TECHNICAL_ANALYSIS = "ta"
    SMART_MONEY_CONCEPTS = "smc"
    ELLIOTT_WAVE = "wave"
    HARMONIC_PATTERNS = "harmonic"
    VOLUME_PROFILE = "profile"
    DERIVATIVES = "derivatives"
    ONCHAIN = "onchain"
    NEWS_SENTIMENT = "news"

class PriceLevel(BaseModel):
    """Price level with optional description"""
    price: float
    description: Optional[str] = None

class RiskManagement(BaseModel):
    """Risk management parameters"""
    stop_loss: PriceLevel
    take_profits: List[PriceLevel]
    trailing_stop: Optional[float] = None  # ATR multiplier
    recommended_leverage: int = Field(ge=1, le=100)
    risk_per_trade: float = Field(ge=0.1, le=10.0)  # percentage
    position_size_usd: Optional[float] = None

class SignalReason(BaseModel):
    """Reason for signal generation"""
    method: AnalysisMethod
    description: str
    confidence: float = Field(ge=0, le=100)
    details: Dict[str, Any] = Field(default_factory=dict)

class Signal(BaseModel):
    """Main signal model"""
    # Basic info
    id: str
    symbol: str
    exchange: str
    direction: SignalDirection
    timeframe: TimeFrame
    
    # Entry and risk management
    entry_price: PriceLevel
    entry_range: Optional[List[float]] = None  # [min, max] for range entries
    risk_management: RiskManagement
    
    # Signal metadata
    confidence: float = Field(ge=0, le=100)
    expected_rr: float = Field(ge=0)  # Risk/Reward ratio
    probability_success: Optional[float] = Field(ge=0, le=1, default=None)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl: timedelta = Field(default=timedelta(hours=24))  # Time to live
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    
    # Analysis reasons
    reasons: List[SignalReason]
    invalidation_conditions: List[str] = Field(default_factory=list)
    
    # Status
    status: SignalStatus = SignalStatus.ACTIVE
    
    # Screenshots and reports
    screenshot_urls: List[str] = Field(default_factory=list)
    report_text: Optional[str] = None
    
    # Tracking
    triggered_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    pnl: Optional[float] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: v.total_seconds()
        }

class MarketData(BaseModel):
    """Market data snapshot"""
    symbol: str
    exchange: str
    timestamp: datetime
    
    # OHLCV
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # Additional data
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    long_short_ratio: Optional[float] = None
    
class AnalysisResult(BaseModel):
    """Result from analysis method"""
    method: AnalysisMethod
    symbol: str
    timeframe: TimeFrame
    confidence: float = Field(ge=0, le=100)
    
    # Analysis specific data
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Potential signals
    potential_signals: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timestamp
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

class UserPreferences(BaseModel):
    """User preferences for signal filtering"""
    user_id: int
    
    # Filters
    symbols: Optional[List[str]] = None
    exchanges: Optional[List[str]] = None
    timeframes: Optional[List[TimeFrame]] = None
    min_confidence: float = Field(default=60.0, ge=0, le=100)
    max_leverage: int = Field(default=10, ge=1, le=100)
    
    # Analysis methods
    enabled_methods: List[AnalysisMethod] = Field(default_factory=lambda: list(AnalysisMethod))
    
    # Risk preferences
    max_risk_per_trade: float = Field(default=2.0, ge=0.1, le=10.0)
    
    # Notification settings
    mute_until: Optional[datetime] = None
    daily_report: bool = True
    weekly_report: bool = True