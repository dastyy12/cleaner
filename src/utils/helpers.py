"""
Utility functions and helpers
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json

logger = logging.getLogger(__name__)

def format_price(price: float, decimals: int = 4) -> str:
    """Format price with appropriate decimal places"""
    try:
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:.4f}"
        elif price >= 0.01:
            return f"{price:.6f}"
        else:
            return f"{price:.8f}"
    except:
        return str(price)

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage value"""
    try:
        return f"{value:.{decimals}f}%"
    except:
        return f"{value}%"

def format_timeframe_display(timeframe: str) -> str:
    """Convert timeframe to display format"""
    tf_map = {
        '1m': '1 минута',
        '5m': '5 минут',
        '15m': '15 минут',
        '1h': '1 час',
        '4h': '4 часа',
        '1d': '1 день'
    }
    return tf_map.get(timeframe, timeframe)

def calculate_position_size(account_balance: float,
                          risk_percentage: float,
                          entry_price: float,
                          stop_loss: float,
                          leverage: int = 1) -> Dict[str, float]:
    """Calculate position size based on risk management"""
    try:
        risk_amount = account_balance * (risk_percentage / 100)
        
        # Calculate stop loss distance
        stop_distance = abs(entry_price - stop_loss) / entry_price
        
        # Position size without leverage
        base_position_size = risk_amount / stop_distance
        
        # Position size with leverage
        leveraged_position_size = base_position_size / leverage
        
        # Quantity calculation
        quantity = leveraged_position_size / entry_price
        
        return {
            'position_size_usd': leveraged_position_size,
            'quantity': quantity,
            'risk_amount': risk_amount,
            'stop_distance_percent': stop_distance * 100
        }
        
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return {
            'position_size_usd': 0,
            'quantity': 0,
            'risk_amount': 0,
            'stop_distance_percent': 0
        }

def validate_signal_data(signal_data: Dict) -> Dict[str, Any]:
    """Validate and sanitize signal data"""
    try:
        validated = {}
        
        # Required fields
        required_fields = ['symbol', 'direction', 'entry_price', 'stop_loss', 'confidence']
        for field in required_fields:
            if field not in signal_data:
                raise ValueError(f"Missing required field: {field}")
            validated[field] = signal_data[field]
        
        # Validate price fields
        price_fields = ['entry_price', 'stop_loss']
        for field in price_fields:
            if not isinstance(validated[field], (int, float)) or validated[field] <= 0:
                raise ValueError(f"Invalid {field}: must be positive number")
        
        # Validate confidence
        if not 0 <= validated['confidence'] <= 100:
            raise ValueError("Confidence must be between 0 and 100")
        
        # Validate direction
        if validated['direction'] not in ['LONG', 'SHORT']:
            raise ValueError("Direction must be LONG or SHORT")
        
        # Optional fields with defaults
        validated['take_profits'] = signal_data.get('take_profits', [])
        validated['timeframe'] = signal_data.get('timeframe', '1h')
        validated['exchange'] = signal_data.get('exchange', 'binance')
        
        return validated
        
    except Exception as e:
        logger.error(f"Signal validation error: {e}")
        raise

def calculate_fibonacci_levels(high: float, low: float) -> Dict[str, float]:
    """Calculate Fibonacci retracement levels"""
    try:
        diff = high - low
        
        levels = {
            '0.0': high,
            '23.6': high - (diff * 0.236),
            '38.2': high - (diff * 0.382),
            '50.0': high - (diff * 0.5),
            '61.8': high - (diff * 0.618),
            '78.6': high - (diff * 0.786),
            '100.0': low
        }
        
        return levels
        
    except Exception as e:
        logger.error(f"Error calculating Fibonacci levels: {e}")
        return {}

def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
    """Calculate pivot point levels"""
    try:
        pivot = (high + low + close) / 3
        
        levels = {
            'PP': pivot,
            'R1': 2 * pivot - low,
            'R2': pivot + (high - low),
            'R3': high + 2 * (pivot - low),
            'S1': 2 * pivot - high,
            'S2': pivot - (high - low),
            'S3': low - 2 * (high - pivot)
        }
        
        return levels
        
    except Exception as e:
        logger.error(f"Error calculating pivot points: {e}")
        return {}

def detect_support_resistance(df: pd.DataFrame, 
                            window: int = 20,
                            min_touches: int = 2) -> Dict[str, List[float]]:
    """Detect support and resistance levels"""
    try:
        support_levels = []
        resistance_levels = []
        
        # Find local highs and lows
        highs = df['high'].rolling(window=window, center=True).max()
        lows = df['low'].rolling(window=window, center=True).min()
        
        # Identify significant levels
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == highs.iloc[i]:
                # Potential resistance
                level = df['high'].iloc[i]
                touches = count_level_touches(df, level, tolerance=0.001)
                if touches >= min_touches:
                    resistance_levels.append(level)
            
            if df['low'].iloc[i] == lows.iloc[i]:
                # Potential support
                level = df['low'].iloc[i]
                touches = count_level_touches(df, level, tolerance=0.001)
                if touches >= min_touches:
                    support_levels.append(level)
        
        # Remove duplicates and sort
        support_levels = sorted(list(set(support_levels)))
        resistance_levels = sorted(list(set(resistance_levels)), reverse=True)
        
        return {
            'support': support_levels[:5],  # Top 5 support levels
            'resistance': resistance_levels[:5]  # Top 5 resistance levels
        }
        
    except Exception as e:
        logger.error(f"Error detecting support/resistance: {e}")
        return {'support': [], 'resistance': []}

def count_level_touches(df: pd.DataFrame, level: float, tolerance: float = 0.001) -> int:
    """Count how many times price touched a level"""
    try:
        touches = 0
        
        for _, row in df.iterrows():
            if (abs(row['high'] - level) / level <= tolerance or
                abs(row['low'] - level) / level <= tolerance):
                touches += 1
        
        return touches
        
    except Exception as e:
        logger.error(f"Error counting level touches: {e}")
        return 0

def calculate_volatility(df: pd.DataFrame, period: int = 20) -> float:
    """Calculate price volatility"""
    try:
        returns = df['close'].pct_change().dropna()
        volatility = returns.rolling(window=period).std().iloc[-1]
        return volatility * np.sqrt(365)  # Annualized volatility
        
    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        return 0.0

def format_signal_message(signal_data: Dict) -> str:
    """Format signal data into readable message"""
    try:
        direction_emoji = "🟢" if signal_data['direction'] == 'LONG' else "🔴"
        
        message = f"""
{direction_emoji} **{signal_data['symbol']} {signal_data['direction']}**

**Entry:** {format_price(signal_data['entry_price'])}
**Stop Loss:** {format_price(signal_data['stop_loss'])}
**Take Profits:**
"""
        
        for i, tp in enumerate(signal_data.get('take_profits', []), 1):
            message += f"  • TP{i}: {format_price(tp)}\n"
        
        message += f"""
**Confidence:** {format_percentage(signal_data['confidence'])}
**Timeframe:** {format_timeframe_display(signal_data.get('timeframe', '1h'))}
**Exchange:** {signal_data.get('exchange', 'Binance').upper()}
        """
        
        return message.strip()
        
    except Exception as e:
        logger.error(f"Error formatting signal message: {e}")
        return "Error formatting signal"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except:
        return default

def normalize_symbol(symbol: str) -> str:
    """Normalize trading symbol format"""
    try:
        # Remove common suffixes and normalize
        symbol = symbol.upper().replace('USDT', '').replace('BUSD', '').replace('USD', '')
        return symbol + 'USDT'
    except:
        return symbol

def validate_timeframe(timeframe: str) -> bool:
    """Validate if timeframe is supported"""
    valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    return timeframe in valid_timeframes

def calculate_risk_reward_ratio(entry: float, stop_loss: float, take_profit: float) -> float:
    """Calculate risk/reward ratio"""
    try:
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        return safe_divide(reward, risk, 0.0)
    except:
        return 0.0

def time_until_expiry(expiry_time: datetime) -> str:
    """Format time until expiry"""
    try:
        now = datetime.utcnow()
        if expiry_time <= now:
            return "Expired"
        
        diff = expiry_time - now
        hours = int(diff.total_seconds() / 3600)
        minutes = int((diff.total_seconds() % 3600) / 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
            
    except:
        return "Unknown"

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    try:
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
    except:
        return [lst]

async def retry_async(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
    """Retry async function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    try:
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
        
    except:
        return "default_filename"

def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    try:
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
        
    except Exception as e:
        logger.error(f"Error merging dictionaries: {e}")
        return dict1

def convert_timeframe_to_minutes(timeframe: str) -> int:
    """Convert timeframe string to minutes"""
    try:
        tf_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        return tf_map.get(timeframe, 60)
    except:
        return 60