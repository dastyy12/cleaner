"""
TradingView Integration - Pine scripts and screenshot generation
"""
import asyncio
import logging
import os
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import aiofiles

# Browser automation
from playwright.async_api import async_playwright, Browser, Page

from config import settings

logger = logging.getLogger(__name__)

class TradingViewIntegration:
    """TradingView integration for charts and screenshots"""
    
    def __init__(self):
        self.config = settings.tradingview
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.initialized = False
        
        # Pine script templates
        self.pine_scripts = {
            'technical_analysis': self._get_ta_pine_script(),
            'smart_money_concepts': self._get_smc_pine_script(),
            'elliott_wave': self._get_wave_pine_script(),
            'harmonic_patterns': self._get_harmonic_pine_script()
        }
        
        # Screenshot storage
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize TradingView integration"""
        try:
            logger.info("🔄 Initializing TradingView Integration...")
            
            # Initialize browser
            await self._init_browser()
            
            # Login to TradingView if credentials provided
            if self.config.tv_username and self.config.tv_password:
                await self._login_tradingview()
            
            self.initialized = True
            logger.info("✅ TradingView Integration initialized")
            
        except Exception as e:
            logger.error(f"❌ TradingView initialization failed: {e}")
            # Don't raise - system should work without TradingView
            logger.warning("⚠️ Continuing without TradingView integration")
    
    async def _init_browser(self):
        """Initialize headless browser"""
        try:
            playwright = await async_playwright().start()
            
            # Launch browser with specific settings for TradingView
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            
            # Create page with TradingView-friendly settings
            self.page = await self.browser.new_page(
                viewport={
                    'width': self.config.screenshot_width,
                    'height': self.config.screenshot_height
                }
            )
            
            # Set user agent
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            logger.info("✅ Browser initialized")
            
        except Exception as e:
            logger.error(f"❌ Browser initialization failed: {e}")
            raise
    
    async def _login_tradingview(self):
        """Login to TradingView"""
        try:
            if not self.page:
                raise Exception("Browser not initialized")
            
            # Navigate to TradingView login
            await self.page.goto("https://www.tradingview.com/accounts/signin/")
            await self.page.wait_for_load_state('networkidle')
            
            # Fill login form
            await self.page.fill('input[name="username"]', self.config.tv_username)
            await self.page.fill('input[name="password"]', self.config.tv_password)
            
            # Submit login
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state('networkidle')
            
            # Check if login was successful
            if await self.page.is_visible('text="Invalid username or password"'):
                raise Exception("Invalid TradingView credentials")
            
            logger.info("✅ TradingView login successful")
            
        except Exception as e:
            logger.error(f"❌ TradingView login failed: {e}")
            # Continue without login - public charts still work
    
    async def generate_chart_screenshot(self,
                                      symbol: str,
                                      exchange: str,
                                      timeframe: str,
                                      analysis_data: Dict[str, Any],
                                      signal_data: Optional[Dict] = None) -> List[str]:
        """
        Generate chart screenshots with analysis overlays
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            exchange: Exchange name (e.g., 'BINANCE')
            timeframe: Chart timeframe (e.g., '1H')
            analysis_data: Analysis results from all methods
            signal_data: Signal information for highlighting
        
        Returns:
            List of screenshot file paths
        """
        try:
            if not self.initialized or not self.page:
                logger.warning("TradingView not initialized, skipping screenshot")
                return []
            
            screenshots = []
            
            # Generate different chart views
            chart_configs = [
                {
                    'name': 'technical_overview',
                    'title': 'Technical Analysis Overview',
                    'indicators': ['ma', 'rsi', 'macd', 'bollinger']
                },
                {
                    'name': 'smc_analysis',
                    'title': 'Smart Money Concepts',
                    'indicators': ['structure', 'fvg', 'order_blocks']
                },
                {
                    'name': 'wave_harmonic',
                    'title': 'Elliott Wave & Harmonic Patterns',
                    'indicators': ['elliott_wave', 'harmonic_patterns', 'fibonacci']
                }
            ]
            
            for config in chart_configs:
                try:
                    screenshot_path = await self._create_chart_screenshot(
                        symbol=symbol,
                        exchange=exchange,
                        timeframe=timeframe,
                        config=config,
                        analysis_data=analysis_data,
                        signal_data=signal_data
                    )
                    
                    if screenshot_path:
                        screenshots.append(screenshot_path)
                        
                except Exception as e:
                    logger.error(f"Error creating {config['name']} screenshot: {e}")
                    continue
            
            return screenshots
            
        except Exception as e:
            logger.error(f"Error generating chart screenshots: {e}")
            return []
    
    async def _create_chart_screenshot(self,
                                     symbol: str,
                                     exchange: str,
                                     timeframe: str,
                                     config: Dict,
                                     analysis_data: Dict,
                                     signal_data: Optional[Dict]) -> Optional[str]:
        """Create a single chart screenshot"""
        try:
            # Build TradingView URL
            tv_symbol = f"{exchange.upper()}:{symbol}"
            chart_url = f"{self.config.tv_chart_url}?symbol={tv_symbol}&interval={timeframe}"
            
            # Navigate to chart
            await self.page.goto(chart_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for chart to load
            await self.page.wait_for_selector('[data-name="legend-source-item"]', timeout=10000)
            await asyncio.sleep(3)  # Additional wait for chart rendering
            
            # Apply chart configuration
            await self._apply_chart_config(config, analysis_data)
            
            # Add signal markers if provided
            if signal_data:
                await self._add_signal_markers(signal_data)
            
            # Take screenshot
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_{exchange}_{timeframe}_{config['name']}_{timestamp}.png"
            screenshot_path = self.screenshot_dir / filename
            
            await self.page.screenshot(
                path=str(screenshot_path),
                full_page=False,
                clip={
                    'x': 0,
                    'y': 0,
                    'width': self.config.screenshot_width,
                    'height': self.config.screenshot_height
                }
            )
            
            logger.info(f"✅ Screenshot saved: {filename}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Error creating chart screenshot: {e}")
            return None
    
    async def _apply_chart_config(self, config: Dict, analysis_data: Dict):
        """Apply chart configuration and indicators"""
        try:
            # This is a simplified version - in practice, you'd need to:
            # 1. Add custom Pine scripts via TradingView's interface
            # 2. Configure indicators based on analysis data
            # 3. Draw levels, zones, and patterns
            
            # For now, we'll add basic indicators available in TradingView
            indicators_to_add = config.get('indicators', [])
            
            for indicator in indicators_to_add:
                try:
                    await self._add_indicator(indicator, analysis_data)
                except Exception as e:
                    logger.warning(f"Failed to add indicator {indicator}: {e}")
                    continue
            
            # Add analysis-specific overlays
            await self._add_analysis_overlays(config['name'], analysis_data)
            
        except Exception as e:
            logger.error(f"Error applying chart config: {e}")
    
    async def _add_indicator(self, indicator: str, analysis_data: Dict):
        """Add a specific indicator to the chart"""
        try:
            # Open indicators panel
            await self.page.click('[data-name="open-indicators-dialog"]')
            await asyncio.sleep(1)
            
            # Search for indicator
            indicator_map = {
                'ma': 'Moving Average',
                'rsi': 'Relative Strength Index',
                'macd': 'MACD',
                'bollinger': 'Bollinger Bands',
                'volume': 'Volume'
            }
            
            if indicator in indicator_map:
                search_term = indicator_map[indicator]
                await self.page.fill('[placeholder="Search"]', search_term)
                await asyncio.sleep(1)
                
                # Click first result
                await self.page.click(f'text="{search_term}"')
                await asyncio.sleep(1)
            
            # Close indicators panel
            await self.page.press('body', 'Escape')
            
        except Exception as e:
            logger.warning(f"Could not add indicator {indicator}: {e}")
    
    async def _add_analysis_overlays(self, chart_type: str, analysis_data: Dict):
        """Add analysis-specific overlays to the chart"""
        try:
            # This would involve drawing custom elements on the chart
            # For now, we'll add text annotations with key findings
            
            if chart_type == 'technical_overview':
                await self._add_technical_annotations(analysis_data)
            elif chart_type == 'smc_analysis':
                await self._add_smc_annotations(analysis_data)
            elif chart_type == 'wave_harmonic':
                await self._add_wave_harmonic_annotations(analysis_data)
                
        except Exception as e:
            logger.error(f"Error adding analysis overlays: {e}")
    
    async def _add_technical_annotations(self, analysis_data: Dict):
        """Add technical analysis annotations"""
        try:
            ta_data = analysis_data.get('technical_analysis', {})
            if not ta_data:
                return
            
            # Add key level annotations
            # This is simplified - real implementation would draw actual levels
            annotations = []
            
            if 'pivot_levels' in ta_data.get('data', {}):
                pivot_data = ta_data['data']['pivot_levels']
                annotations.append(f"Pivot: {pivot_data.get('pivot', 'N/A'):.4f}")
            
            if 'rsi' in ta_data.get('data', {}):
                rsi_value = ta_data['data']['rsi'][-1] if isinstance(ta_data['data']['rsi'], list) else None
                if rsi_value:
                    annotations.append(f"RSI: {rsi_value:.1f}")
            
            # Add annotations to chart (simplified)
            for i, annotation in enumerate(annotations[:3]):  # Limit to 3 annotations
                await self._add_text_annotation(annotation, i)
                
        except Exception as e:
            logger.error(f"Error adding technical annotations: {e}")
    
    async def _add_smc_annotations(self, analysis_data: Dict):
        """Add Smart Money Concepts annotations"""
        try:
            smc_data = analysis_data.get('smart_money_concepts', {})
            if not smc_data:
                return
            
            annotations = []
            
            # Market structure
            structure = smc_data.get('data', {}).get('market_structure', {})
            if structure:
                annotations.append(f"Structure: {structure.get('type', 'Unknown')}")
            
            # BOS/CHOCH events
            bos_choch = smc_data.get('data', {}).get('bos_choch', [])
            if bos_choch:
                latest_event = bos_choch[-1]
                annotations.append(f"{latest_event.get('type', 'BOS')}: {latest_event.get('direction', 'N/A')}")
            
            # FVG zones
            fvg_zones = smc_data.get('data', {}).get('fair_value_gaps', [])
            if fvg_zones:
                annotations.append(f"FVG Zones: {len(fvg_zones)}")
            
            for i, annotation in enumerate(annotations[:3]):
                await self._add_text_annotation(annotation, i)
                
        except Exception as e:
            logger.error(f"Error adding SMC annotations: {e}")
    
    async def _add_wave_harmonic_annotations(self, analysis_data: Dict):
        """Add Elliott Wave and Harmonic pattern annotations"""
        try:
            annotations = []
            
            # Elliott Wave
            wave_data = analysis_data.get('elliott_wave', {})
            if wave_data:
                wave_count = wave_data.get('data', {}).get('current_wave_count', {})
                if wave_count:
                    annotations.append(f"Wave: {wave_count.get('primary_count', 'Unknown')}")
            
            # Harmonic Patterns
            harmonic_data = analysis_data.get('harmonic_patterns', {})
            if harmonic_data:
                patterns = harmonic_data.get('data', {}).get('detected_patterns', [])
                if patterns:
                    best_pattern = patterns[0]
                    annotations.append(f"Pattern: {best_pattern.get('type', {}).get('value', 'Unknown')}")
            
            for i, annotation in enumerate(annotations[:3]):
                await self._add_text_annotation(annotation, i)
                
        except Exception as e:
            logger.error(f"Error adding wave/harmonic annotations: {e}")
    
    async def _add_text_annotation(self, text: str, position: int):
        """Add a text annotation to the chart"""
        try:
            # This is a simplified implementation
            # Real implementation would use TradingView's drawing tools API
            
            # Try to add drawing tools (if available)
            await self.page.evaluate(f"""
                // Add text annotation (this is pseudo-code)
                console.log('Adding annotation: {text} at position {position}');
            """)
            
        except Exception as e:
            logger.debug(f"Could not add text annotation: {e}")
    
    async def _add_signal_markers(self, signal_data: Dict):
        """Add signal entry/exit markers to the chart"""
        try:
            # Add visual markers for signal entry points
            entry_price = signal_data.get('entry_price')
            stop_loss = signal_data.get('stop_loss')
            take_profits = signal_data.get('take_profits', [])
            
            if entry_price:
                # Add entry marker (simplified)
                await self.page.evaluate(f"""
                    console.log('Signal Entry: {entry_price}');
                """)
            
            if stop_loss:
                await self.page.evaluate(f"""
                    console.log('Stop Loss: {stop_loss}');
                """)
            
            for i, tp in enumerate(take_profits):
                await self.page.evaluate(f"""
                    console.log('Take Profit {i+1}: {tp}');
                """)
                
        except Exception as e:
            logger.error(f"Error adding signal markers: {e}")
    
    def _get_ta_pine_script(self) -> str:
        """Get Pine script for technical analysis indicators"""
        return """
//@version=5
indicator("Crypto Signals - Technical Analysis", shorttitle="CS-TA", overlay=true)

// Moving Averages
ma9 = ta.sma(close, 9)
ma21 = ta.sma(close, 21)
ma50 = ta.sma(close, 50)
ma200 = ta.sma(close, 200)

plot(ma9, "MA9", color.yellow, 1)
plot(ma21, "MA21", color.orange, 2)
plot(ma50, "MA50", color.blue, 2)
plot(ma200, "MA200", color.red, 3)

// VWAP
vwap_line = ta.vwap(hlc3)
plot(vwap_line, "VWAP", color.purple, 2)

// Support/Resistance Levels
pivot_high = ta.pivothigh(high, 5, 5)
pivot_low = ta.pivotlow(low, 5, 5)

plotshape(pivot_high, "Resistance", shape.triangledown, location.abovebar, color.red, size=size.small)
plotshape(pivot_low, "Support", shape.triangleup, location.belowbar, color.green, size=size.small)
"""
    
    def _get_smc_pine_script(self) -> str:
        """Get Pine script for Smart Money Concepts"""
        return """
//@version=5
indicator("Crypto Signals - Smart Money Concepts", shorttitle="CS-SMC", overlay=true)

// Market Structure
swing_length = 5
pivot_high = ta.pivothigh(high, swing_length, swing_length)
pivot_low = ta.pivotlow(low, swing_length, swing_length)

// BOS/CHOCH Detection (simplified)
var float last_high = na
var float last_low = na

if not na(pivot_high)
    last_high := pivot_high
if not na(pivot_low)
    last_low := pivot_low

// Fair Value Gaps (simplified)
gap_up = low[1] > high[2]
gap_down = high[1] < low[2]

bgcolor(gap_up ? color.new(color.green, 80) : na, title="Bullish FVG")
bgcolor(gap_down ? color.new(color.red, 80) : na, title="Bearish FVG")

// Order Blocks (simplified)
bullish_ob = close[1] < open[1] and close > high[1]
bearish_ob = close[1] > open[1] and close < low[1]

plotshape(bullish_ob, "Bullish OB", shape.square, location.belowbar, color.green, size=size.small)
plotshape(bearish_ob, "Bearish OB", shape.square, location.abovebar, color.red, size=size.small)
"""
    
    def _get_wave_pine_script(self) -> str:
        """Get Pine script for Elliott Wave analysis"""
        return """
//@version=5
indicator("Crypto Signals - Elliott Wave", shorttitle="CS-EW", overlay=true)

// Simplified Elliott Wave Detection
swing_length = 8
pivot_high = ta.pivothigh(high, swing_length, swing_length)
pivot_low = ta.pivotlow(low, swing_length, swing_length)

// Fibonacci Levels
var float wave_start = na
var float wave_end = na

if not na(pivot_high) or not na(pivot_low)
    wave_start := nz(wave_end, close)
    wave_end := not na(pivot_high) ? pivot_high : pivot_low

// Draw Fibonacci Retracements (simplified)
fib_236 = wave_start + (wave_end - wave_start) * 0.236
fib_382 = wave_start + (wave_end - wave_start) * 0.382
fib_618 = wave_start + (wave_end - wave_start) * 0.618

plot(fib_236, "Fib 23.6%", color.gray, 1, plot.style_linebr)
plot(fib_382, "Fib 38.2%", color.yellow, 1, plot.style_linebr)
plot(fib_618, "Fib 61.8%", color.orange, 2, plot.style_linebr)
"""
    
    def _get_harmonic_pine_script(self) -> str:
        """Get Pine script for harmonic patterns"""
        return """
//@version=5
indicator("Crypto Signals - Harmonic Patterns", shorttitle="CS-HP", overlay=true)

// Simplified Harmonic Pattern Detection
swing_length = 5

// Find XABCD Points
X = ta.pivothigh(high, swing_length, swing_length)
A = ta.pivotlow(low, swing_length, swing_length)
B = ta.pivothigh(high, swing_length, swing_length)
C = ta.pivotlow(low, swing_length, swing_length)
D = ta.pivothigh(high, swing_length, swing_length)

// Pattern Recognition (simplified Gartley)
var float x_price = na
var float a_price = na
var float b_price = na
var float c_price = na

if not na(X)
    x_price := X
if not na(A)
    a_price := A
if not na(B)
    b_price := B
if not na(C)
    c_price := C

// Draw pattern lines (simplified)
plotshape(not na(X), "X", shape.labeldown, location.abovebar, color.blue, text="X", size=size.small)
plotshape(not na(A), "A", shape.labelup, location.belowbar, color.red, text="A", size=size.small)
plotshape(not na(B), "B", shape.labeldown, location.abovebar, color.blue, text="B", size=size.small)
plotshape(not na(C), "C", shape.labelup, location.belowbar, color.red, text="C", size=size.small)
"""
    
    async def stop(self):
        """Stop TradingView integration"""
        try:
            if self.page:
                await self.page.close()
            
            if self.browser:
                await self.browser.close()
            
            logger.info("✅ TradingView integration stopped")
            
        except Exception as e:
            logger.error(f"Error stopping TradingView integration: {e}")
    
    async def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """Clean up old screenshot files"""
        try:
            import time
            current_time = time.time()
            
            for screenshot_file in self.screenshot_dir.glob("*.png"):
                file_age = current_time - screenshot_file.stat().st_mtime
                if file_age > (max_age_hours * 3600):
                    screenshot_file.unlink()
                    logger.debug(f"Deleted old screenshot: {screenshot_file.name}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up screenshots: {e}")
    
    def get_screenshot_url(self, screenshot_path: str) -> str:
        """Convert local screenshot path to URL (for web serving)"""
        try:
            # This would return a URL where the screenshot can be accessed
            # For now, return the local path
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error getting screenshot URL: {e}")
            return screenshot_path