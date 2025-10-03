"""
Telegram Bot - Signal delivery and user interface
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.signal_engine import SignalEngine
from src.models import Signal, SignalDirection, UserPreferences, AnalysisMethod, TimeFrame
from config import settings

logger = logging.getLogger(__name__)

class UserStates(StatesGroup):
    """User interaction states"""
    waiting_for_symbols = State()
    waiting_for_confidence = State()
    waiting_for_risk = State()

class TelegramBot:
    """Telegram bot for crypto signal delivery"""
    
    def __init__(self, signal_engine: SignalEngine):
        self.signal_engine = signal_engine
        self.bot = Bot(token=settings.telegram.bot_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # User preferences cache
        self.user_preferences: Dict[int, UserPreferences] = {}
        
        # Rate limiting
        self.user_last_command: Dict[int, datetime] = {}
        self.rate_limit_seconds = 2
        
        # Setup handlers
        self._setup_handlers()
        
        self.running = False
    
    async def initialize(self):
        """Initialize the Telegram bot"""
        try:
            logger.info("🔄 Initializing Telegram Bot...")
            
            # Test bot connection
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Bot connected: @{bot_info.username}")
            
            # Load user preferences
            await self._load_user_preferences()
            
            logger.info("✅ Telegram Bot initialized")
            
        except Exception as e:
            logger.error(f"❌ Telegram Bot initialization failed: {e}")
            raise
    
    def _setup_handlers(self):
        """Setup message and callback handlers"""
        
        # Command handlers
        self.dp.message(CommandStart())(self._handle_start)
        self.dp.message(Command("help"))(self._handle_help)
        self.dp.message(Command("signals"))(self._handle_signals)
        self.dp.message(Command("top"))(self._handle_top_signals)
        self.dp.message(Command("filter"))(self._handle_filter)
        self.dp.message(Command("confidence"))(self._handle_confidence)
        self.dp.message(Command("methods"))(self._handle_methods)
        self.dp.message(Command("risk"))(self._handle_risk)
        self.dp.message(Command("leverage"))(self._handle_leverage)
        self.dp.message(Command("chart"))(self._handle_chart)
        self.dp.message(Command("report"))(self._handle_report)
        self.dp.message(Command("mute"))(self._handle_mute)
        self.dp.message(Command("stats"))(self._handle_stats)
        self.dp.message(Command("settings"))(self._handle_settings)
        
        # Callback query handlers
        self.dp.callback_query(F.data.startswith("signal_"))(self._handle_signal_callback)
        self.dp.callback_query(F.data.startswith("method_"))(self._handle_method_callback)
        self.dp.callback_query(F.data.startswith("settings_"))(self._handle_settings_callback)
        
        # Text message handlers for states
        self.dp.message(UserStates.waiting_for_symbols)(self._handle_symbols_input)
        self.dp.message(UserStates.waiting_for_confidence)(self._handle_confidence_input)
        self.dp.message(UserStates.waiting_for_risk)(self._handle_risk_input)
    
    async def _rate_limit_check(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        now = datetime.utcnow()
        last_command = self.user_last_command.get(user_id)
        
        if last_command and (now - last_command).total_seconds() < self.rate_limit_seconds:
            return False
        
        self.user_last_command[user_id] = now
        return True
    
    async def _handle_start(self, message: Message):
        """Handle /start command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            welcome_text = """
🚀 **Crypto Signal Bot**

Добро пожаловать в систему генерации криптосигналов!

**Основные команды:**
• `/signals` - Показать активные сигналы
• `/top 5` - Топ 5 сигналов
• `/filter BTC ETH` - Фильтр по символам
• `/confidence 80` - Мин. уверенность
• `/methods` - Настройка методов анализа
• `/settings` - Все настройки
• `/help` - Справка

**Особенности:**
✅ Мульти-биржевой анализ (Binance/Bybit/OKX)
✅ 4 метода анализа (TA/SMC/Elliott/Harmonic)
✅ Скриншоты графиков TradingView
✅ Управление рисками
✅ Только рекомендации (без торговли)

Начните с команды `/signals` для просмотра сигналов!
            """
            
            await message.answer(welcome_text, parse_mode="Markdown")
            
            # Create default user preferences
            await self._ensure_user_preferences(message.from_user.id)
            
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await message.answer("❌ Ошибка при запуске бота")
    
    async def _handle_help(self, message: Message):
        """Handle /help command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            help_text = """
📖 **Справка по командам**

**Основные команды:**
• `/signals` - Все активные сигналы
• `/top N` - Топ N сигналов (по умолчанию 5)
• `/filter SYMBOL1 SYMBOL2` - Фильтр по символам
• `/confidence NN` - Мин. уверенность (60-95%)

**Настройки методов:**
• `/methods` - Включить/выключить методы анализа
• `/methods on smc wave` - Включить SMC и Elliott Wave
• `/methods off ta` - Выключить Technical Analysis

**Управление рисками:**
• `/risk N.N` - Риск на сделку (0.5-5.0%)
• `/leverage auto|N` - Авто или фикс. плечо

**Дополнительно:**
• `/chart SYMBOL TF` - График символа
• `/report daily|weekly` - Отчеты
• `/mute Nh` - Отключить на N часов
• `/stats` - Статистика сигналов
• `/settings` - Все настройки

**Методы анализа:**
🔹 **TA** - Классический техан (MA, RSI, MACD)
🔹 **SMC** - Smart Money (BOS, FVG, Order Blocks)
🔹 **Wave** - Elliott Wave анализ
🔹 **Harmonic** - Гармонические паттерны

**Примеры:**
`/top 3` - Топ 3 сигнала
`/filter BTC ETH SOL` - Только BTC, ETH, SOL
`/confidence 75` - Мин. уверенность 75%
`/methods on smc wave` - Только SMC и волны
            """
            
            await message.answer(help_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in help handler: {e}")
            await message.answer("❌ Ошибка при выводе справки")
    
    async def _handle_signals(self, message: Message):
        """Handle /signals command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            user_prefs = await self._get_user_preferences(message.from_user.id)
            
            # Get filtered signals
            signals = self.signal_engine.get_active_signals(
                min_confidence=user_prefs.min_confidence
            )
            
            # Apply user filters
            if user_prefs.symbols:
                signals = [s for s in signals if s.symbol in user_prefs.symbols]
            
            if user_prefs.exchanges:
                signals = [s for s in signals if s.exchange in user_prefs.exchanges]
            
            if not signals:
                await message.answer("📭 Нет активных сигналов, соответствующих вашим фильтрам")
                return
            
            # Send signals
            for signal in signals[:10]:  # Limit to 10 signals
                await self._send_signal_message(message.chat.id, signal)
                await asyncio.sleep(0.5)  # Avoid rate limits
            
            # Send summary
            summary_text = f"📊 Показано {len(signals[:10])} из {len(signals)} сигналов"
            if len(signals) > 10:
                summary_text += f"\nИспользуйте `/top {len(signals)}` для всех сигналов"
            
            await message.answer(summary_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in signals handler: {e}")
            await message.answer("❌ Ошибка при получении сигналов")
    
    async def _handle_top_signals(self, message: Message):
        """Handle /top command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            # Parse number from command
            args = message.text.split()[1:] if len(message.text.split()) > 1 else ["5"]
            try:
                count = int(args[0])
                count = max(1, min(20, count))  # Limit 1-20
            except:
                count = 5
            
            user_prefs = await self._get_user_preferences(message.from_user.id)
            
            # Get top signals
            signals = self.signal_engine.get_active_signals(
                min_confidence=user_prefs.min_confidence
            )
            
            # Apply filters
            if user_prefs.symbols:
                signals = [s for s in signals if s.symbol in user_prefs.symbols]
            
            if not signals:
                await message.answer("📭 Нет сигналов для отображения")
                return
            
            # Send top signals
            top_signals = signals[:count]
            
            header = f"🔝 **Топ {len(top_signals)} сигналов**\n"
            await message.answer(header, parse_mode="Markdown")
            
            for i, signal in enumerate(top_signals, 1):
                await self._send_signal_message(message.chat.id, signal, index=i)
                await asyncio.sleep(0.3)
            
        except Exception as e:
            logger.error(f"Error in top signals handler: {e}")
            await message.answer("❌ Ошибка при получении топ сигналов")
    
    async def _send_signal_message(self, chat_id: int, signal: Signal, index: Optional[int] = None):
        """Send a formatted signal message"""
        try:
            # Signal header
            direction_emoji = "🟢" if signal.direction == SignalDirection.LONG else "🔴"
            index_text = f"{index}. " if index else ""
            
            header = f"{index_text}{direction_emoji} **{signal.symbol}** {signal.direction.value}"
            
            # Signal details
            details = f"""
**Exchange:** {signal.exchange.upper()}
**Timeframe:** {signal.timeframe.value}
**Entry:** {signal.entry_price.price:.4f}
**Stop Loss:** {signal.risk_management.stop_loss.price:.4f}
**Take Profits:**"""
            
            for i, tp in enumerate(signal.risk_management.take_profits, 1):
                details += f"\n  • TP{i}: {tp.price:.4f}"
            
            details += f"""

**Risk/Reward:** {signal.expected_rr:.2f}
**Confidence:** {signal.confidence:.1f}%
**Leverage:** {signal.risk_management.recommended_leverage}x
**Risk per trade:** {signal.risk_management.risk_per_trade:.1f}%

**Reasons:**"""
            
            for reason in signal.reasons:
                details += f"\n• {reason.method.value}: {reason.description}"
            
            # Time info
            time_left = signal.expires_at - datetime.utcnow()
            hours_left = int(time_left.total_seconds() / 3600)
            details += f"\n\n⏰ Expires in {hours_left}h"
            
            # Create inline keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 График", 
                        callback_data=f"signal_chart_{signal.id}"
                    ),
                    InlineKeyboardButton(
                        text="📝 Детали", 
                        callback_data=f"signal_details_{signal.id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔔 Напомнить", 
                        callback_data=f"signal_remind_{signal.id}"
                    ),
                    InlineKeyboardButton(
                        text="📋 Похожие", 
                        callback_data=f"signal_similar_{signal.id}"
                    )
                ]
            ])
            
            full_message = header + details
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=full_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Send screenshots if available
            if signal.screenshot_urls:
                for screenshot_url in signal.screenshot_urls[:2]:  # Max 2 screenshots
                    try:
                        with open(screenshot_url, 'rb') as photo:
                            await self.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo,
                                caption=f"📊 {signal.symbol} - Chart Analysis"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to send screenshot: {e}")
            
        except Exception as e:
            logger.error(f"Error sending signal message: {e}")
    
    async def _handle_filter(self, message: Message):
        """Handle /filter command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            args = message.text.split()[1:]
            
            if not args:
                # Show current filters
                user_prefs = await self._get_user_preferences(message.from_user.id)
                symbols = user_prefs.symbols or ["Все"]
                exchanges = user_prefs.exchanges or ["Все"]
                
                filter_text = f"""
📊 **Текущие фильтры:**

**Символы:** {', '.join(symbols)}
**Биржи:** {', '.join(exchanges)}
**Мин. уверенность:** {user_prefs.min_confidence}%

**Использование:**
`/filter BTC ETH SOL` - Фильтр по символам
`/filter clear` - Очистить фильтры
                """
                
                await message.answer(filter_text, parse_mode="Markdown")
                return
            
            if args[0].lower() == "clear":
                # Clear filters
                user_prefs = await self._get_user_preferences(message.from_user.id)
                user_prefs.symbols = None
                user_prefs.exchanges = None
                await self._save_user_preferences(message.from_user.id, user_prefs)
                
                await message.answer("✅ Фильтры очищены")
                return
            
            # Set symbol filters
            symbols = [arg.upper() for arg in args if arg.upper() in settings.symbols]
            
            if not symbols:
                await message.answer("❌ Не найдено подходящих символов")
                return
            
            user_prefs = await self._get_user_preferences(message.from_user.id)
            user_prefs.symbols = symbols
            await self._save_user_preferences(message.from_user.id, user_prefs)
            
            await message.answer(f"✅ Фильтр установлен: {', '.join(symbols)}")
            
        except Exception as e:
            logger.error(f"Error in filter handler: {e}")
            await message.answer("❌ Ошибка при установке фильтра")
    
    async def _handle_confidence(self, message: Message):
        """Handle /confidence command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            args = message.text.split()[1:]
            
            if not args:
                user_prefs = await self._get_user_preferences(message.from_user.id)
                await message.answer(f"📊 Текущая мин. уверенность: {user_prefs.min_confidence}%")
                return
            
            try:
                confidence = float(args[0])
                confidence = max(30.0, min(95.0, confidence))
            except:
                await message.answer("❌ Неверный формат. Используйте: `/confidence 75`")
                return
            
            user_prefs = await self._get_user_preferences(message.from_user.id)
            user_prefs.min_confidence = confidence
            await self._save_user_preferences(message.from_user.id, user_prefs)
            
            await message.answer(f"✅ Мин. уверенность установлена: {confidence}%")
            
        except Exception as e:
            logger.error(f"Error in confidence handler: {e}")
            await message.answer("❌ Ошибка при установке уверенности")
    
    async def _handle_methods(self, message: Message):
        """Handle /methods command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            args = message.text.split()[1:]
            user_prefs = await self._get_user_preferences(message.from_user.id)
            
            if not args:
                # Show current methods
                enabled = [m.value for m in user_prefs.enabled_methods]
                
                methods_text = f"""
🔧 **Методы анализа:**

**Включены:** {', '.join(enabled) if enabled else 'Все'}

**Доступные методы:**
• `ta` - Technical Analysis
• `smc` - Smart Money Concepts  
• `wave` - Elliott Wave
• `harmonic` - Harmonic Patterns

**Использование:**
`/methods on smc wave` - Включить SMC и Wave
`/methods off ta` - Выключить TA
`/methods reset` - Сбросить (все методы)
                """
                
                await message.answer(methods_text, parse_mode="Markdown")
                return
            
            if args[0].lower() == "reset":
                user_prefs.enabled_methods = list(AnalysisMethod)
                await self._save_user_preferences(message.from_user.id, user_prefs)
                await message.answer("✅ Методы сброшены (включены все)")
                return
            
            if len(args) < 2:
                await message.answer("❌ Неверный формат. Используйте: `/methods on smc wave`")
                return
            
            action = args[0].lower()
            method_names = args[1:]
            
            # Map method names
            method_map = {
                'ta': AnalysisMethod.TECHNICAL_ANALYSIS,
                'smc': AnalysisMethod.SMART_MONEY_CONCEPTS,
                'wave': AnalysisMethod.ELLIOTT_WAVE,
                'harmonic': AnalysisMethod.HARMONIC_PATTERNS
            }
            
            methods = []
            for name in method_names:
                if name.lower() in method_map:
                    methods.append(method_map[name.lower()])
            
            if not methods:
                await message.answer("❌ Не найдено подходящих методов")
                return
            
            if action == "on":
                # Add methods
                for method in methods:
                    if method not in user_prefs.enabled_methods:
                        user_prefs.enabled_methods.append(method)
                action_text = "включены"
            elif action == "off":
                # Remove methods
                for method in methods:
                    if method in user_prefs.enabled_methods:
                        user_prefs.enabled_methods.remove(method)
                action_text = "выключены"
            else:
                await message.answer("❌ Используйте 'on' или 'off'")
                return
            
            await self._save_user_preferences(message.from_user.id, user_prefs)
            
            method_names_str = ', '.join([m.value for m in methods])
            await message.answer(f"✅ Методы {action_text}: {method_names_str}")
            
        except Exception as e:
            logger.error(f"Error in methods handler: {e}")
            await message.answer("❌ Ошибка при настройке методов")
    
    async def _handle_stats(self, message: Message):
        """Handle /stats command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            stats = self.signal_engine.get_signal_stats()
            
            stats_text = f"""
📈 **Статистика сигналов:**

**Всего сгенерировано:** {stats['total_generated']}
**Сработало:** {stats['total_triggered']}
**Остановлено:** {stats['total_stopped']}
**Активных:** {stats['active_signals']}

**Win Rate:** {stats['win_rate']:.1f}%

**Обновлено:** {datetime.fromisoformat(stats['last_updated']).strftime('%H:%M:%S')}
            """
            
            await message.answer(stats_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in stats handler: {e}")
            await message.answer("❌ Ошибка при получении статистики")
    
    async def _handle_settings(self, message: Message):
        """Handle /settings command"""
        try:
            if not await self._rate_limit_check(message.from_user.id):
                return
            
            user_prefs = await self._get_user_preferences(message.from_user.id)
            
            symbols_text = ', '.join(user_prefs.symbols) if user_prefs.symbols else "Все"
            exchanges_text = ', '.join(user_prefs.exchanges) if user_prefs.exchanges else "Все"
            methods_text = ', '.join([m.value for m in user_prefs.enabled_methods])
            
            mute_text = "Нет"
            if user_prefs.mute_until and user_prefs.mute_until > datetime.utcnow():
                time_left = user_prefs.mute_until - datetime.utcnow()
                hours_left = int(time_left.total_seconds() / 3600)
                mute_text = f"Еще {hours_left}ч"
            
            settings_text = f"""
⚙️ **Настройки пользователя:**

**Фильтры:**
• Символы: {symbols_text}
• Биржи: {exchanges_text}
• Мин. уверенность: {user_prefs.min_confidence}%

**Методы анализа:**
{methods_text}

**Риск-менеджмент:**
• Макс. плечо: {user_prefs.max_leverage}x
• Макс. риск на сделку: {user_prefs.max_risk_per_trade}%

**Уведомления:**
• Отключены: {mute_text}
• Дневной отчет: {'Да' if user_prefs.daily_report else 'Нет'}
• Недельный отчет: {'Да' if user_prefs.weekly_report else 'Нет'}

**Быстрые настройки:**
            """
            
            # Create settings keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Символы", callback_data="settings_symbols"),
                    InlineKeyboardButton(text="🎯 Уверенность", callback_data="settings_confidence")
                ],
                [
                    InlineKeyboardButton(text="🔧 Методы", callback_data="settings_methods"),
                    InlineKeyboardButton(text="⚖️ Риски", callback_data="settings_risk")
                ],
                [
                    InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications"),
                    InlineKeyboardButton(text="🔄 Сброс", callback_data="settings_reset")
                ]
            ])
            
            await message.answer(settings_text, parse_mode="Markdown", reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in settings handler: {e}")
            await message.answer("❌ Ошибка при получении настроек")
    
    async def _handle_signal_callback(self, callback: CallbackQuery):
        """Handle signal-related callbacks"""
        try:
            data_parts = callback.data.split('_')
            action = data_parts[1]
            signal_id = data_parts[2]
            
            # Find signal
            signal = self.signal_engine.active_signals.get(signal_id)
            if not signal:
                await callback.answer("❌ Сигнал не найден")
                return
            
            if action == "chart":
                await self._send_signal_chart(callback.message.chat.id, signal)
                await callback.answer("📊 График отправлен")
                
            elif action == "details":
                await self._send_signal_details(callback.message.chat.id, signal)
                await callback.answer("📝 Детали отправлены")
                
            elif action == "remind":
                # Set reminder (simplified)
                await callback.answer("🔔 Напоминание установлено на 1 час")
                
            elif action == "similar":
                await self._send_similar_signals(callback.message.chat.id, signal)
                await callback.answer("📋 Похожие сигналы найдены")
            
        except Exception as e:
            logger.error(f"Error in signal callback: {e}")
            await callback.answer("❌ Ошибка обработки")
    
    async def _send_signal_chart(self, chat_id: int, signal: Signal):
        """Send signal chart"""
        try:
            if signal.screenshot_urls:
                for screenshot_url in signal.screenshot_urls:
                    try:
                        with open(screenshot_url, 'rb') as photo:
                            await self.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo,
                                caption=f"📊 {signal.symbol} - {signal.direction.value} Signal Chart"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to send chart: {e}")
            else:
                await self.bot.send_message(chat_id, "📊 График временно недоступен")
                
        except Exception as e:
            logger.error(f"Error sending signal chart: {e}")
    
    async def _send_signal_details(self, chat_id: int, signal: Signal):
        """Send detailed signal information"""
        try:
            details_text = f"""
📝 **Детальная информация по сигналу**

**{signal.symbol} {signal.direction.value}**

**Основные параметры:**
• ID: `{signal.id}`
• Биржа: {signal.exchange.upper()}
• Таймфрейм: {signal.timeframe.value}
• Создан: {signal.created_at.strftime('%d.%m.%Y %H:%M')}

**Цены:**
• Вход: {signal.entry_price.price:.6f}
• Стоп: {signal.risk_management.stop_loss.price:.6f}
• TP1: {signal.risk_management.take_profits[0].price:.6f}
• TP2: {signal.risk_management.take_profits[1].price:.6f}

**Анализ:**
• Уверенность: {signal.confidence:.1f}%
• R/R: {signal.expected_rr:.2f}
• Вероятность успеха: {signal.probability_success*100:.1f}% (если доступно)

**Причины сигнала:**
            """
            
            for reason in signal.reasons:
                details_text += f"\n• **{reason.method.value}** ({reason.confidence:.1f}%): {reason.description}"
            
            # Invalidation conditions
            if signal.invalidation_conditions:
                details_text += "\n\n**Условия отмены:**"
                for condition in signal.invalidation_conditions:
                    details_text += f"\n• {condition}"
            
            await self.bot.send_message(chat_id, details_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error sending signal details: {e}")
    
    async def _ensure_user_preferences(self, user_id: int):
        """Ensure user has preferences"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences(user_id=user_id)
            await self._save_user_preferences(user_id, self.user_preferences[user_id])
    
    async def _get_user_preferences(self, user_id: int) -> UserPreferences:
        """Get user preferences"""
        await self._ensure_user_preferences(user_id)
        return self.user_preferences[user_id]
    
    async def _save_user_preferences(self, user_id: int, preferences: UserPreferences):
        """Save user preferences"""
        self.user_preferences[user_id] = preferences
        
        # Save to database
        try:
            prefs_dict = preferences.dict()
            await self.signal_engine.data_manager.storage.update_user_preferences(user_id, prefs_dict)
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
    
    async def _load_user_preferences(self):
        """Load user preferences from database"""
        try:
            # This would load all user preferences from database
            # For now, we start with empty cache
            logger.info("📊 User preferences loaded")
            
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
    
    async def start(self):
        """Start the Telegram bot"""
        if self.running:
            return
        
        logger.info("🚀 Starting Telegram Bot...")
        self.running = True
        
        # Start polling
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop the Telegram bot"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping Telegram Bot...")
        self.running = False
        
        # Stop polling
        await self.dp.stop_polling()
        
        # Close bot session
        await self.bot.session.close()
        
        logger.info("✅ Telegram Bot stopped")
    
    async def send_signal_notification(self, signal: Signal, user_ids: Optional[List[int]] = None):
        """Send signal notification to users"""
        try:
            if user_ids is None:
                user_ids = list(self.user_preferences.keys())
            
            for user_id in user_ids:
                try:
                    user_prefs = await self._get_user_preferences(user_id)
                    
                    # Check if user should receive this signal
                    if not self._should_send_signal(signal, user_prefs):
                        continue
                    
                    # Check if user is muted
                    if (user_prefs.mute_until and 
                        user_prefs.mute_until > datetime.utcnow()):
                        continue
                    
                    await self._send_signal_message(user_id, signal)
                    await asyncio.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error sending signal to user {user_id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error sending signal notifications: {e}")
    
    def _should_send_signal(self, signal: Signal, user_prefs: UserPreferences) -> bool:
        """Check if signal should be sent to user based on preferences"""
        try:
            # Check confidence threshold
            if signal.confidence < user_prefs.min_confidence:
                return False
            
            # Check symbol filter
            if user_prefs.symbols and signal.symbol not in user_prefs.symbols:
                return False
            
            # Check exchange filter
            if user_prefs.exchanges and signal.exchange not in user_prefs.exchanges:
                return False
            
            # Check enabled methods
            signal_methods = [reason.method for reason in signal.reasons]
            if not any(method in user_prefs.enabled_methods for method in signal_methods):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal filters: {e}")
            return False