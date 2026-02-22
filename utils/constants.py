"""
Константы задачи варианта №10
"""

# Цветовая схема приложения (бело-синяя)
COLORS = {
    'primary': '#1560BD',      # Джинсовый синий
    'primary_light': '#4A7DB5',
    'primary_dark': '#0E3D7A',
    'secondary': '#F0F4FA',    # Светло-синий для фона
    'background': '#FFFFFF',    # Белый фон
    'surface': '#F8FAFE',       # Поверхности
    'text': '#2C3E50',          # Темно-синий для текста
    'text_light': '#6C7A89',    # Светлый текст
    'success': '#27AE60',       # Зеленый для успеха
    'warning': '#E67E22',       # Оранжевый для предупреждений
    'error': '#E74C3C',         # Красный для ошибок
    'border': '#D5DCE5',        # Цвет границ
    'hover': '#E8EEF5'          # Цвет при наведении
}

# Характеристики инвестиционных инструментов
INVESTMENTS = [
    {'name': 'A', 'start_months': [1, 2, 3, 4, 5, 6], 'duration': 1, 'rate': 1.5, 'risk': 2},
    {'name': 'B', 'start_months': [1, 3, 5], 'duration': 2, 'rate': 3.5, 'risk': 6},
    {'name': 'C', 'start_months': [1, 4], 'duration': 3, 'rate': 6.0, 'risk': 9},
    {'name': 'O', 'start_months': [1], 'duration': 6, 'rate': 11.0, 'risk': 10}
]

# Платежи по контракту
PAYMENTS = {
    2: 200,
    6: 700
}

# Ограничения по умолчанию
RISK_LIMIT = 6.0
DURATION_LIMIT = 2.5

# Настройки приложения
APP_NAME = "Инвестиционный оптимизатор - Задача Г. Альба"
APP_VERSION = "1.0.0"
APP_WIDTH = 1300
APP_HEIGHT = 850