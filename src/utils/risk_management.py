"""
Risk Management Utilities
Advanced position sizing, leverage calculation, and risk assessment
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from src.models import Signal, SignalDirection
from config import settings

logger = logging.getLogger(__name__)

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self):
        self.max_risk_per_trade = settings.analysis.default_risk_per_trade
        self.max_leverage = settings.analysis.max_leverage
        self.max_daily_risk = 5.0  # Maximum daily risk percentage
        self.max_weekly_risk = 10.0  # Maximum weekly risk percentage
        
        # Risk limits by asset type
        self.asset_risk_limits = {
            'BTC': {'max_leverage': 10, 'max_risk': 3.0},
            'ETH': {'max_leverage': 8, 'max_risk': 3.0},
            'major_alts': {'max_leverage': 5, 'max_risk': 2.5},  # Top 10 coins
            'alts': {'max_leverage': 3, 'max_risk': 2.0},        # Other coins
            'meme': {'max_leverage': 2, 'max_risk': 1.5}         # Meme coins
        }
        
        # Volatility-based adjustments
        self.volatility_thresholds = {
            'low': 0.02,    # < 2% daily volatility
            'medium': 0.05, # 2-5% daily volatility
            'high': 0.10,   # 5-10% daily volatility
            'extreme': 0.20 # > 10% daily volatility
        }
    
    def calculate_optimal_position_size(self,
                                      account_balance: float,
                                      signal: Signal,
                                      market_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Calculate optimal position size based on multiple risk factors
        
        Args:
            account_balance: Total account balance in USD
            signal: Trading signal with entry/SL/TP
            market_data: Additional market data for risk assessment
        
        Returns:
            Dictionary with position sizing recommendations
        """
        try:
            # Basic risk parameters
            entry_price = signal.entry_price.price
            stop_loss = signal.risk_management.stop_loss.price
            
            # Calculate base risk amount
            base_risk_amount = account_balance * (self.max_risk_per_trade / 100)
            
            # Adjust risk based on signal confidence
            confidence_multiplier = self._get_confidence_multiplier(signal.confidence)
            adjusted_risk_amount = base_risk_amount * confidence_multiplier
            
            # Calculate stop loss distance
            stop_distance = abs(entry_price - stop_loss) / entry_price
            
            # Base position size (without leverage)
            base_position_size = adjusted_risk_amount / stop_distance
            
            # Calculate optimal leverage
            optimal_leverage = self._calculate_optimal_leverage(
                signal, market_data, stop_distance
            )
            
            # Final position size with leverage
            position_size_usd = base_position_size / optimal_leverage
            quantity = position_size_usd / entry_price
            
            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(
                signal, position_size_usd, optimal_leverage, account_balance
            )
            
            # Position sizing recommendations
            recommendations = self._generate_position_recommendations(
                signal, risk_metrics, market_data
            )
            
            return {
                'position_size_usd': position_size_usd,
                'quantity': quantity,
                'optimal_leverage': optimal_leverage,
                'risk_amount': adjusted_risk_amount,
                'risk_percentage': (adjusted_risk_amount / account_balance) * 100,
                'stop_distance_percent': stop_distance * 100,
                'confidence_multiplier': confidence_multiplier,
                'risk_metrics': risk_metrics,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self._get_conservative_position_size(account_balance, signal)
    
    def _get_confidence_multiplier(self, confidence: float) -> float:
        """Get position size multiplier based on signal confidence"""
        try:
            if confidence >= 90:
                return 1.2  # Increase position by 20%
            elif confidence >= 80:
                return 1.1  # Increase position by 10%
            elif confidence >= 70:
                return 1.0  # Normal position
            elif confidence >= 60:
                return 0.8  # Reduce position by 20%
            else:
                return 0.5  # Reduce position by 50%
                
        except:
            return 1.0
    
    def _calculate_optimal_leverage(self,
                                  signal: Signal,
                                  market_data: Optional[Dict],
                                  stop_distance: float) -> int:
        """Calculate optimal leverage based on multiple factors"""
        try:
            # Start with base leverage from signal
            base_leverage = signal.risk_management.recommended_leverage
            
            # Asset-specific limits
            asset_limits = self._get_asset_risk_limits(signal.symbol)
            max_asset_leverage = asset_limits['max_leverage']
            
            # Volatility adjustment
            volatility_multiplier = 1.0
            if market_data and 'volatility' in market_data:
                volatility_multiplier = self._get_volatility_multiplier(
                    market_data['volatility']
                )
            
            # Stop distance adjustment (tighter stops allow higher leverage)
            stop_multiplier = min(2.0, max(0.5, 0.02 / stop_distance))
            
            # Calculate optimal leverage
            optimal_leverage = int(
                base_leverage * volatility_multiplier * stop_multiplier
            )
            
            # Apply limits
            optimal_leverage = min(
                optimal_leverage,
                max_asset_leverage,
                self.max_leverage
            )
            optimal_leverage = max(1, optimal_leverage)
            
            return optimal_leverage
            
        except Exception as e:
            logger.error(f"Error calculating optimal leverage: {e}")
            return 1
    
    def _get_asset_risk_limits(self, symbol: str) -> Dict[str, float]:
        """Get risk limits for specific asset"""
        try:
            symbol_clean = symbol.replace('USDT', '').replace('BUSD', '')
            
            if symbol_clean in ['BTC']:
                return self.asset_risk_limits['BTC']
            elif symbol_clean in ['ETH']:
                return self.asset_risk_limits['ETH']
            elif symbol_clean in ['ADA', 'SOL', 'DOT', 'LINK', 'MATIC', 'AVAX', 'ATOM']:
                return self.asset_risk_limits['major_alts']
            elif symbol_clean in ['DOGE', 'SHIB', 'PEPE']:
                return self.asset_risk_limits['meme']
            else:
                return self.asset_risk_limits['alts']
                
        except:
            return self.asset_risk_limits['alts']
    
    def _get_volatility_multiplier(self, volatility: float) -> float:
        """Get leverage multiplier based on volatility"""
        try:
            if volatility <= self.volatility_thresholds['low']:
                return 1.2  # Low volatility allows higher leverage
            elif volatility <= self.volatility_thresholds['medium']:
                return 1.0  # Normal leverage
            elif volatility <= self.volatility_thresholds['high']:
                return 0.8  # Reduce leverage for high volatility
            else:
                return 0.5  # Significantly reduce for extreme volatility
                
        except:
            return 1.0
    
    def _calculate_risk_metrics(self,
                              signal: Signal,
                              position_size: float,
                              leverage: int,
                              account_balance: float) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        try:
            entry_price = signal.entry_price.price
            stop_loss = signal.risk_management.stop_loss.price
            take_profits = signal.risk_management.take_profits
            
            # Basic metrics
            notional_value = position_size * leverage
            margin_required = position_size
            margin_ratio = (margin_required / account_balance) * 100
            
            # Risk calculations
            max_loss = abs(entry_price - stop_loss) / entry_price * notional_value
            max_loss_percent = (max_loss / account_balance) * 100
            
            # Reward calculations
            potential_rewards = []
            for tp in take_profits:
                reward = abs(tp.price - entry_price) / entry_price * notional_value
                potential_rewards.append(reward)
            
            avg_reward = np.mean(potential_rewards) if potential_rewards else 0
            risk_reward_ratio = avg_reward / max_loss if max_loss > 0 else 0
            
            # Liquidation price (approximate)
            liquidation_price = self._calculate_liquidation_price(
                entry_price, leverage, signal.direction
            )
            
            # Distance to liquidation
            liquidation_distance = abs(entry_price - liquidation_price) / entry_price * 100
            
            return {
                'notional_value': notional_value,
                'margin_required': margin_required,
                'margin_ratio_percent': margin_ratio,
                'max_loss_usd': max_loss,
                'max_loss_percent': max_loss_percent,
                'potential_rewards': potential_rewards,
                'avg_reward_usd': avg_reward,
                'risk_reward_ratio': risk_reward_ratio,
                'liquidation_price': liquidation_price,
                'liquidation_distance_percent': liquidation_distance
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def _calculate_liquidation_price(self,
                                   entry_price: float,
                                   leverage: int,
                                   direction: SignalDirection) -> float:
        """Calculate approximate liquidation price"""
        try:
            # Simplified liquidation calculation (assumes 0.5% maintenance margin)
            maintenance_margin_rate = 0.005
            
            if direction == SignalDirection.LONG:
                # Long liquidation: entry * (1 - 1/leverage + maintenance_margin)
                liquidation_price = entry_price * (1 - (1/leverage) + maintenance_margin_rate)
            else:
                # Short liquidation: entry * (1 + 1/leverage - maintenance_margin)
                liquidation_price = entry_price * (1 + (1/leverage) - maintenance_margin_rate)
            
            return liquidation_price
            
        except:
            return 0.0
    
    def _generate_position_recommendations(self,
                                         signal: Signal,
                                         risk_metrics: Dict,
                                         market_data: Optional[Dict]) -> List[str]:
        """Generate position sizing recommendations"""
        try:
            recommendations = []
            
            # Risk level assessment
            max_loss_percent = risk_metrics.get('max_loss_percent', 0)
            if max_loss_percent > 3.0:
                recommendations.append("⚠️ High risk trade - consider reducing position size")
            elif max_loss_percent < 1.0:
                recommendations.append("✅ Conservative risk level")
            
            # Leverage assessment
            leverage = risk_metrics.get('leverage', 1)
            if leverage > 5:
                recommendations.append("⚡ High leverage - monitor closely for volatility")
            
            # Liquidation distance
            liq_distance = risk_metrics.get('liquidation_distance_percent', 100)
            if liq_distance < 10:
                recommendations.append("🚨 Liquidation price too close - reduce leverage")
            elif liq_distance < 20:
                recommendations.append("⚠️ Monitor liquidation distance")
            
            # Risk/Reward ratio
            rr_ratio = risk_metrics.get('risk_reward_ratio', 0)
            if rr_ratio < 1.5:
                recommendations.append("📉 Low R/R ratio - consider better entry or wider TP")
            elif rr_ratio > 3.0:
                recommendations.append("📈 Excellent R/R ratio")
            
            # Confidence-based recommendations
            if signal.confidence < 70:
                recommendations.append("🤔 Lower confidence - consider smaller position")
            elif signal.confidence > 85:
                recommendations.append("🎯 High confidence signal")
            
            # Market conditions
            if market_data and market_data.get('volatility', 0) > 0.1:
                recommendations.append("🌪️ High volatility - use tighter stops")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["⚠️ Unable to generate recommendations"]
    
    def _get_conservative_position_size(self,
                                      account_balance: float,
                                      signal: Signal) -> Dict[str, Any]:
        """Get conservative position size as fallback"""
        try:
            # Very conservative approach
            risk_amount = account_balance * 0.01  # 1% risk
            entry_price = signal.entry_price.price
            stop_loss = signal.risk_management.stop_loss.price
            
            stop_distance = abs(entry_price - stop_loss) / entry_price
            position_size = risk_amount / stop_distance
            quantity = position_size / entry_price
            
            return {
                'position_size_usd': position_size,
                'quantity': quantity,
                'optimal_leverage': 1,
                'risk_amount': risk_amount,
                'risk_percentage': 1.0,
                'stop_distance_percent': stop_distance * 100,
                'confidence_multiplier': 0.5,
                'risk_metrics': {},
                'recommendations': ["⚠️ Using conservative fallback sizing"]
            }
            
        except Exception as e:
            logger.error(f"Error calculating conservative position size: {e}")
            return {
                'position_size_usd': 100,
                'quantity': 100 / signal.entry_price.price,
                'optimal_leverage': 1,
                'risk_amount': account_balance * 0.01,
                'risk_percentage': 1.0,
                'recommendations': ["❌ Error in position calculation - using minimal size"]
            }
    
    def validate_position_limits(self,
                               user_id: int,
                               new_position: Dict,
                               existing_positions: List[Dict]) -> Dict[str, Any]:
        """Validate position against user limits and existing exposure"""
        try:
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'errors': [],
                'adjustments': {}
            }
            
            # Calculate total exposure
            total_risk = new_position.get('risk_percentage', 0)
            for pos in existing_positions:
                total_risk += pos.get('risk_percentage', 0)
            
            # Daily risk limit check
            if total_risk > self.max_daily_risk:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"Total risk ({total_risk:.1f}%) exceeds daily limit ({self.max_daily_risk}%)"
                )
            
            # Position concentration check
            symbol_exposure = new_position.get('position_size_usd', 0)
            for pos in existing_positions:
                if pos.get('symbol') == new_position.get('symbol'):
                    symbol_exposure += pos.get('position_size_usd', 0)
            
            # Warn if more than 30% in one symbol
            account_balance = sum(pos.get('account_balance', 0) for pos in [new_position])
            if symbol_exposure / account_balance > 0.3:
                validation_result['warnings'].append(
                    "High concentration in single asset (>30%)"
                )
            
            # Leverage check
            leverage = new_position.get('optimal_leverage', 1)
            if leverage > self.max_leverage:
                validation_result['adjustments']['leverage'] = self.max_leverage
                validation_result['warnings'].append(
                    f"Leverage reduced from {leverage}x to {self.max_leverage}x"
                )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating position limits: {e}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {e}"],
                'warnings': [],
                'adjustments': {}
            }
    
    def calculate_portfolio_risk(self, positions: List[Dict]) -> Dict[str, Any]:
        """Calculate overall portfolio risk metrics"""
        try:
            if not positions:
                return {'total_risk': 0, 'max_drawdown': 0, 'correlation_risk': 0}
            
            # Total risk calculation
            total_risk = sum(pos.get('risk_percentage', 0) for pos in positions)
            
            # Maximum potential drawdown
            max_drawdown = sum(pos.get('max_loss_percent', 0) for pos in positions)
            
            # Asset correlation risk (simplified)
            symbols = [pos.get('symbol', '') for pos in positions]
            unique_symbols = len(set(symbols))
            correlation_risk = (len(symbols) - unique_symbols) / len(symbols) if symbols else 0
            
            # Risk distribution
            risk_by_asset = {}
            for pos in positions:
                symbol = pos.get('symbol', 'UNKNOWN')
                risk_by_asset[symbol] = risk_by_asset.get(symbol, 0) + pos.get('risk_percentage', 0)
            
            return {
                'total_risk_percent': total_risk,
                'max_potential_drawdown_percent': max_drawdown,
                'correlation_risk': correlation_risk,
                'position_count': len(positions),
                'unique_assets': unique_symbols,
                'risk_by_asset': risk_by_asset,
                'largest_position_risk': max(pos.get('risk_percentage', 0) for pos in positions),
                'average_position_risk': total_risk / len(positions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {'error': str(e)}
    
    def suggest_risk_adjustments(self, portfolio_risk: Dict) -> List[str]:
        """Suggest risk management adjustments based on portfolio analysis"""
        try:
            suggestions = []
            
            total_risk = portfolio_risk.get('total_risk_percent', 0)
            max_drawdown = portfolio_risk.get('max_potential_drawdown_percent', 0)
            correlation_risk = portfolio_risk.get('correlation_risk', 0)
            
            # Total risk suggestions
            if total_risk > 15:
                suggestions.append("🚨 Total portfolio risk very high - consider closing some positions")
            elif total_risk > 10:
                suggestions.append("⚠️ High portfolio risk - avoid new positions")
            elif total_risk < 3:
                suggestions.append("📈 Low risk utilization - room for more positions")
            
            # Drawdown suggestions
            if max_drawdown > 20:
                suggestions.append("💥 Potential drawdown too high - tighten stops")
            
            # Correlation suggestions
            if correlation_risk > 0.5:
                suggestions.append("🔗 High correlation risk - diversify across different assets")
            
            # Position count suggestions
            position_count = portfolio_risk.get('position_count', 0)
            if position_count > 10:
                suggestions.append("📊 Many open positions - consider consolidation")
            elif position_count < 3:
                suggestions.append("🎯 Few positions - consider diversification")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating risk suggestions: {e}")
            return ["❌ Unable to generate risk suggestions"]