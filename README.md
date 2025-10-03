# Crypto Signal Generation System

Комплексная система генерации криптосигналов в реальном времени с мульти-биржевым анализом и интеграцией TradingView.

## 🚀 Особенности

### Анализ и Сигналы
- **Мульти-биржевой анализ**: Binance, Bybit, OKX
- **4 метода анализа**:
  - 📊 **Technical Analysis** - Классический техан (MA, RSI, MACD, Bollinger)
  - 💰 **Smart Money Concepts** - BOS/CHOCH, FVG, Order Blocks, ликвидность
  - 🌊 **Elliott Wave** - Авто-разметка волн с Fibonacci
  - 🎯 **Harmonic Patterns** - Gartley, Bat, Butterfly, Crab, Cypher, Shark
- **Скриншоты TradingView** с разметкой анализа
- **Управление рисками** - автоматический расчет SL/TP, плечо, размер позиции

### Telegram Bot
- **Умная фильтрация** сигналов по символам, уверенности, методам
- **Интерактивные команды** - `/signals`, `/top`, `/filter`, `/confidence`
- **Персональные настройки** для каждого пользователя
- **Визуальные отчеты** с графиками и детальным анализом
- **Мультиязычность** (RU/EN)

### Техническая архитектура
- **Высокопроизводительное хранение**: ClickHouse + Redis + PostgreSQL
- **Масштабируемость**: Docker + Kubernetes ready
- **Мониторинг**: Prometheus + Grafana
- **Безопасность**: Только рекомендации, без торговых ключей

## 📋 Требования

- Python 3.11+
- Docker & Docker Compose
- Telegram Bot Token
- TradingView аккаунт (опционально)

## 🛠 Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-repo/crypto-signals.git
cd crypto-signals
```

### 2. Настройка окружения
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

### 3. Запуск с Docker
```bash
# Запуск основных сервисов
docker-compose up -d

# Запуск с мониторингом (Grafana + Prometheus)
docker-compose --profile monitoring up -d
```

### 4. Локальная разработка
```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка TA-Lib (Linux/Mac)
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make && sudo make install

# Установка Playwright браузеров
playwright install chromium

# Запуск приложения
python main.py
```

## ⚙️ Конфигурация

### Основные настройки (.env)
```env
# Обязательные
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_chat_id

# Опциональные API ключи для расширенного доступа к данным
BINANCE_API_KEY=your_binance_api_key
BYBIT_API_KEY=your_bybit_api_key
OKX_API_KEY=your_okx_api_key

# TradingView для скриншотов
TV_USERNAME=your_tradingview_username
TV_PASSWORD=your_tradingview_password
```

### Поддерживаемые символы
По умолчанию: BTC, ETH, ADA, SOL, DOT, LINK, MATIC, AVAX, ATOM, NEAR, FTM, SAND, MANA, GALA, ENJ

### Таймфреймы
1m, 5m, 15m, 1h, 4h, 1d

## 🤖 Команды Telegram Bot

### Основные команды
- `/start` - Начало работы с ботом
- `/help` - Справка по всем командам
- `/signals` - Показать все активные сигналы
- `/top N` - Топ N сигналов по уверенности
- `/stats` - Статистика работы системы

### Фильтрация и настройки
- `/filter BTC ETH SOL` - Фильтр по символам
- `/confidence 75` - Минимальная уверенность (60-95%)
- `/methods on smc wave` - Включить методы анализа
- `/methods off ta` - Выключить методы
- `/risk 1.5` - Риск на сделку (0.5-5.0%)
- `/leverage auto` - Автоматическое плечо

### Дополнительные функции
- `/chart BTCUSDT 1h` - График символа
- `/report daily` - Дневной отчет
- `/mute 2h` - Отключить уведомления
- `/settings` - Все настройки пользователя

## 📊 Структура сигнала

Каждый сигнал содержит:

```
🟢 BTCUSDT LONG
Exchange: BINANCE
Timeframe: 1h
Entry: 43,250.00
Stop Loss: 42,800.00
Take Profits:
  • TP1: 44,100.00
  • TP2: 45,200.00

Risk/Reward: 2.1
Confidence: 78.5%
Leverage: 3x
Risk per trade: 2.0%

Reasons:
• Technical Analysis: RSI oversold bounce
• Smart Money Concepts: FVG zone test
• Elliott Wave: Wave 5 completion expected

⏰ Expires in 18h
```

## 🏗 Архитектура системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Analysis       │    │   Signal        │
│                 │    │                  │    │   Engine        │
│ • Binance       │───▶│ • Technical      │───▶│                 │
│ • Bybit         │    │ • Smart Money    │    │ • Confidence    │
│ • OKX           │    │ • Elliott Wave   │    │ • Risk Mgmt     │
│ • On-chain      │    │ • Harmonic       │    │ • Validation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Storage       │    │   TradingView    │    │   Telegram      │
│                 │    │                  │    │   Bot           │
│ • ClickHouse    │    │ • Screenshots    │    │                 │
│ • Redis         │    │ • Pine Scripts   │    │ • User Mgmt     │
│ • PostgreSQL    │    │ • Chart Analysis │    │ • Notifications │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔍 Методы анализа

### 1. Technical Analysis (TA)
- **Тренд**: MA/EMA/HMA, MACD, ADX
- **Моментум**: RSI, Stochastic, CCI
- **Волатильность**: ATR, Bollinger Bands, Keltner Channels
- **Уровни**: Pivot Points, Support/Resistance, VWAP, Fibonacci

### 2. Smart Money Concepts (SMC)
- **Структура рынка**: BOS/CHOCH, HH/HL/LH/LL
- **Зоны ликвидности**: EQH/EQL, FVG (Fair Value Gaps)
- **Order Blocks**: Bullish/Bearish OB
- **Premium/Discount зоны**: на основе диапазонов

### 3. Elliott Wave
- **Авто-разметка**: Импульсы (1-5) и коррекции (ABC)
- **Fibonacci соотношения**: 0.382, 0.618, 1.618, 2.618
- **Валидация правил**: Elliott Wave принципы
- **Проекции**: Цели для незавершенных волн

### 4. Harmonic Patterns
- **XABCD паттерны**: Gartley, Bat, Butterfly, Crab, Deep Crab, Cypher, Shark
- **PRZ зоны**: Potential Reversal Zones
- **Fibonacci точность**: Допуск 5% для соотношений
- **Confluence**: Пересечение нескольких паттернов

## 📈 Мониторинг

### Grafana Dashboards
- **Signal Performance**: Win rate, R/R, методы
- **System Health**: Uptime, errors, latency
- **Market Data**: Volume, volatility, coverage
- **User Activity**: Commands, preferences, engagement

### Prometheus Metrics
- `signals_generated_total` - Всего сигналов
- `signals_success_rate` - Процент успешных сигналов
- `analysis_duration_seconds` - Время анализа
- `telegram_commands_total` - Команды пользователей

## 🔒 Безопасность

- **Только рекомендации** - никаких торговых операций
- **Шифрование API ключей** в переменных окружения
- **Rate limiting** для Telegram команд
- **Валидация входных данных** на всех уровнях
- **Логирование** всех операций для аудита

## 🚀 Производительность

- **Параллельная обработка** анализа по методам
- **Кэширование** результатов в Redis
- **Батчинг** операций с базой данных
- **Асинхронная архитектура** для высокой пропускной способности
- **Оптимизированные запросы** к биржевым API

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/

# Тесты с покрытием
pytest --cov=src tests/

# Линтинг
flake8 src/
black src/
```

## 📝 Логирование

Логи сохраняются в:
- `logs/crypto_signals.log` - Основные логи
- `logs/error.log` - Только ошибки
- `logs/telegram.log` - Telegram bot логи
- `logs/signals.log` - История сигналов

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE).

## ⚠️ Дисклеймер

**Этот бот предоставляет только образовательную информацию и торговые идеи. Не является инвестиционным советом. Торговля криптовалютами сопряжена с высокими рисками. Всегда проводите собственный анализ перед принятием торговых решений.**

## 📞 Поддержка

- 📧 Email: support@crypto-signals.com
- 💬 Telegram: @crypto_signals_support
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/crypto-signals/issues)
- 📖 Документация: [Wiki](https://github.com/your-repo/crypto-signals/wiki)

---

**Made with ❤️ for the crypto community**