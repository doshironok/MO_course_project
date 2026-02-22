"""
Модуль вкладки визуализации
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from utils.constants import COLORS


class MplCanvas(FigureCanvas):
    """Виджет для отображения графиков matplotlib"""

    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor(COLORS['background'])
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor(COLORS['surface'])
        super().__init__(self.fig)


class ChartsTab(QWidget):
    """
    Вкладка для визуализации результатов
    """

    def __init__(self):
        super().__init__()
        self.current_solution = None
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel("Визуализация результатов")
        title_label.setProperty("role", "heading")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Панель управления
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)

        control_layout.addWidget(QLabel("📊 Тип графика:"))

        self.chart_combo = QComboBox()
        self.chart_combo.addItems([
            "Структура портфеля по инструментам",
            "Динамика риска по месяцам",
            "Динамика срока погашения",
            "Сравнение сценариев"
        ])
        self.chart_combo.setMinimumWidth(250)
        self.chart_combo.currentIndexChanged.connect(self.update_chart)
        control_layout.addWidget(self.chart_combo)

        control_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setProperty("class", "secondary")
        self.refresh_btn.clicked.connect(self.update_chart)
        control_layout.addWidget(self.refresh_btn)

        layout.addWidget(control_frame)

        # Область графика
        self.canvas = MplCanvas(self, width=12, height=7)
        layout.addWidget(self.canvas)

        # Статус
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['secondary']};
                border-radius: 5px;
                padding: 8px;
            }}
        """)
        status_layout = QHBoxLayout(status_frame)

        self.status_label = QLabel("Выберите тип графика для отображения")
        self.status_label.setStyleSheet(f"color: {COLORS['text_light']};")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        self.setLayout(layout)

    def set_solution(self, solution: dict):
        """Установка решения для визуализации"""
        self.current_solution = solution
        self.update_chart()

    def update_chart(self):
        """Обновление графика в соответствии с выбранным типом"""
        if not self.current_solution or not self.current_solution.get('success', False):
            self.status_label.setText("❌ Нет данных для визуализации")
            self.canvas.axes.clear()
            self.canvas.axes.text(0.5, 0.5, 'Нет данных для отображения',
                                 ha='center', va='center', fontsize=14,
                                 color=COLORS['text_light'])
            self.canvas.draw()
            return

        chart_type = self.chart_combo.currentIndex()

        self.canvas.axes.clear()

        # Настройка стиля графика
        self.canvas.axes.tick_params(colors=COLORS['text'])
        self.canvas.axes.spines['bottom'].set_color(COLORS['border'])
        self.canvas.axes.spines['top'].set_color(COLORS['border'])
        self.canvas.axes.spines['left'].set_color(COLORS['border'])
        self.canvas.axes.spines['right'].set_color(COLORS['border'])

        if chart_type == 0:
            self._plot_structure()
        elif chart_type == 1:
            self._plot_risk_dynamics()
        elif chart_type == 2:
            self._plot_duration_dynamics()
        elif chart_type == 3:
            self._plot_comparison()

        self.canvas.fig.tight_layout()
        self.canvas.draw()
        self.status_label.setText(f"✓ Отображен график: {self.chart_combo.currentText()}")

    def _plot_structure(self):
        """Построение графика структуры портфеля"""
        allocation = self.current_solution.get('allocation', {})

        # Агрегация по инструментам
        instruments = {}
        for key, alloc in allocation.items():
            instr = alloc['instrument']
            if instr not in instruments:
                instruments[instr] = 0
            instruments[instr] += alloc['amount']

        if not instruments:
            self.canvas.axes.text(0.5, 0.5, "Нет данных", ha='center', va='center')
            return

        names = list(instruments.keys())
        values = list(instruments.values())

        # Цветовая схема
        colors = [COLORS['primary'], COLORS['primary_light'],
                 '#4A7DB5', '#6C8EB5']

        bars = self.canvas.axes.bar(names, values, color=colors[:len(names)],
                                   edgecolor=COLORS['border'], linewidth=2)

        self.canvas.axes.set_title('Структура инвестиционного портфеля по инструментам',
                                  color=COLORS['primary'], fontsize=14, fontweight='bold')
        self.canvas.axes.set_xlabel('Инструмент', color=COLORS['text'])
        self.canvas.axes.set_ylabel('Сумма инвестиций (млн руб)', color=COLORS['text'])

        # Добавление подписей значений
        for bar in bars:
            height = bar.get_height()
            self.canvas.axes.text(bar.get_x() + bar.get_width()/2., height,
                                 f'{height:,.1f}'.replace(',', ' '),
                                 ha='center', va='bottom', fontweight='bold',
                                 color=COLORS['primary'])

        self.canvas.axes.grid(True, alpha=0.3, color=COLORS['border'])
        self.canvas.axes.set_axisbelow(True)

    def _plot_risk_dynamics(self):
        """Построение графика динамики риска"""
        monthly_risk = self.current_solution.get('monthly_risk', [])
        risk_limit = self.current_solution.get('risk_limit', 6)

        months = list(range(1, 7))

        # Линия фактического риска
        self.canvas.axes.plot(months, monthly_risk, 'o-', linewidth=3, markersize=10,
                             label='Фактический риск', color=COLORS['primary'],
                             markerfacecolor='white', markeredgewidth=2,
                             markeredgecolor=COLORS['primary'])

        # Линия лимита
        self.canvas.axes.axhline(y=risk_limit, color=COLORS['error'], linestyle='--',
                                linewidth=2, label=f'Лимит ({risk_limit})')

        # Заливка области превышения
        for i, (month, risk) in enumerate(zip(months, monthly_risk)):
            if risk > risk_limit:
                self.canvas.axes.fill_between([month-0.2, month+0.2], risk_limit, risk,
                                             color=COLORS['error'], alpha=0.3)

        self.canvas.axes.set_title('Динамика средневзвешенного риска по месяцам',
                                  color=COLORS['primary'], fontsize=14, fontweight='bold')
        self.canvas.axes.set_xlabel('Месяц', color=COLORS['text'])
        self.canvas.axes.set_ylabel('Риск', color=COLORS['text'])
        self.canvas.axes.set_xticks(months)
        self.canvas.axes.legend(loc='upper right', framealpha=1,
                               facecolor=COLORS['surface'])
        self.canvas.axes.grid(True, alpha=0.3, color=COLORS['border'])
        self.canvas.axes.set_axisbelow(True)

    def _plot_duration_dynamics(self):
        """Построение графика динамики срока погашения"""
        monthly_duration = self.current_solution.get('monthly_duration', [])
        duration_limit = self.current_solution.get('duration_limit', 2.5)

        months = list(range(1, 7))

        # Линия фактического срока
        self.canvas.axes.plot(months, monthly_duration, 's-', linewidth=3, markersize=10,
                             label='Фактический срок', color=COLORS['primary_light'],
                             markerfacecolor='white', markeredgewidth=2,
                             markeredgecolor=COLORS['primary_light'])

        # Линия лимита
        self.canvas.axes.axhline(y=duration_limit, color=COLORS['error'], linestyle='--',
                                linewidth=2, label=f'Лимит ({duration_limit})')

        # Заливка области превышения
        for i, (month, duration) in enumerate(zip(months, monthly_duration)):
            if duration > duration_limit:
                self.canvas.axes.fill_between([month-0.2, month+0.2], duration_limit, duration,
                                             color=COLORS['error'], alpha=0.3)

        self.canvas.axes.set_title('Динамика среднего срока до погашения по месяцам',
                                  color=COLORS['primary'], fontsize=14, fontweight='bold')
        self.canvas.axes.set_xlabel('Месяц', color=COLORS['text'])
        self.canvas.axes.set_ylabel('Срок (месяцы)', color=COLORS['text'])
        self.canvas.axes.set_xticks(months)
        self.canvas.axes.legend(loc='upper right', framealpha=1,
                               facecolor=COLORS['surface'])
        self.canvas.axes.grid(True, alpha=0.3, color=COLORS['border'])
        self.canvas.axes.set_axisbelow(True)

    def _plot_comparison(self):
        """Построение сравнительной диаграммы для разных сценариев"""
        if self.current_solution:
            fun_value = self.current_solution.get('fun', 0)
            mode = self.current_solution.get('mode', 'basic')

            mode_names = {'basic': 'Без\nограничений', 'risk': 'С\nриском', 'full': 'Полный'}

            colors = [COLORS['primary'], COLORS['primary_light'], '#4A7DB5']

            bars = self.canvas.axes.bar([mode_names.get(mode, mode)], [fun_value],
                                       color=colors[0], alpha=0.8,
                                       edgecolor=COLORS['border'], linewidth=2)

            self.canvas.axes.set_title('Начальный фонд для текущего сценария',
                                      color=COLORS['primary'], fontsize=14, fontweight='bold')
            self.canvas.axes.set_ylabel('Начальный фонд (млн руб)', color=COLORS['text'])

            # Добавление подписи значения
            for bar in bars:
                height = bar.get_height()
                self.canvas.axes.text(bar.get_x() + bar.get_width()/2., height,
                                     f'{height:,.1f}'.replace(',', ' '),
                                     ha='center', va='bottom', fontweight='bold',
                                     color=COLORS['primary'])

        self.canvas.axes.grid(True, alpha=0.3, color=COLORS['border'])
        self.canvas.axes.set_axisbelow(True)