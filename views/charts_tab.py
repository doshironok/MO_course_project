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


class MplCanvas(FigureCanvas):
    """Виджет для отображения графиков matplotlib"""

    def __init__(self, parent=None, width=8, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
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

        # Панель выбора типа графика
        control_panel = QHBoxLayout()

        control_panel.addWidget(QLabel("Тип графика:"))

        self.chart_combo = QComboBox()
        self.chart_combo.addItems([
            "Структура портфеля по инструментам",
            "Динамика риска по месяцам",
            "Динамика срока погашения",
            "Сравнение сценариев"
        ])
        self.chart_combo.currentIndexChanged.connect(self.update_chart)
        control_panel.addWidget(self.chart_combo)

        control_panel.addStretch()

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.update_chart)
        control_panel.addWidget(self.refresh_btn)

        layout.addLayout(control_panel)

        # Область графика
        self.canvas = MplCanvas(self, width=10, height=6)
        layout.addWidget(self.canvas)

        # Статус
        self.status_label = QLabel("Выберите тип графика для отображения")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def set_solution(self, solution: dict):
        """Установка решения для визуализации"""
        self.current_solution = solution
        self.update_chart()

    def update_chart(self):
        """Обновление графика в соответствии с выбранным типом"""
        if not self.current_solution or not self.current_solution.get('success', False):
            self.status_label.setText("Нет данных для визуализации")
            self.canvas.axes.clear()
            self.canvas.draw()
            return

        chart_type = self.chart_combo.currentIndex()

        self.canvas.axes.clear()

        if chart_type == 0:
            self._plot_structure()
        elif chart_type == 1:
            self._plot_risk_dynamics()
        elif chart_type == 2:
            self._plot_duration_dynamics()
        elif chart_type == 3:
            self._plot_comparison()

        self.canvas.draw()
        self.status_label.setText(f"Отображен график: {self.chart_combo.currentText()}")

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
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

        bars = self.canvas.axes.bar(names, values, color=colors[:len(names)])
        self.canvas.axes.set_title('Структура инвестиционного портфеля по инструментам')
        self.canvas.axes.set_xlabel('Инструмент')
        self.canvas.axes.set_ylabel('Сумма инвестиций (млн руб)')

        # Добавление подписей значений
        for bar in bars:
            height = bar.get_height()
            self.canvas.axes.text(bar.get_x() + bar.get_width() / 2., height,
                                  f'{height:.1f}', ha='center', va='bottom')

        self.canvas.axes.grid(True, alpha=0.3)

    def _plot_risk_dynamics(self):
        """Построение графика динамики риска"""
        monthly_risk = self.current_solution.get('monthly_risk', [])
        risk_limit = self.current_solution.get('risk_limit', 6)

        months = list(range(1, 7))

        self.canvas.axes.plot(months, monthly_risk, 'o-', linewidth=2, markersize=8,
                              label='Фактический риск', color='#FF6B6B')
        self.canvas.axes.axhline(y=risk_limit, color='#4ECDC4', linestyle='--',
                                 linewidth=2, label=f'Лимит ({risk_limit})')

        self.canvas.axes.set_title('Динамика средневзвешенного риска по месяцам')
        self.canvas.axes.set_xlabel('Месяц')
        self.canvas.axes.set_ylabel('Риск')
        self.canvas.axes.set_xticks(months)
        self.canvas.axes.legend()
        self.canvas.axes.grid(True, alpha=0.3)

    def _plot_duration_dynamics(self):
        """Построение графика динамики срока погашения"""
        monthly_duration = self.current_solution.get('monthly_duration', [])
        duration_limit = self.current_solution.get('duration_limit', 2.5)

        months = list(range(1, 7))

        self.canvas.axes.plot(months, monthly_duration, 'o-', linewidth=2, markersize=8,
                              label='Фактический срок', color='#45B7D1')
        self.canvas.axes.axhline(y=duration_limit, color='#4ECDC4', linestyle='--',
                                 linewidth=2, label=f'Лимит ({duration_limit})')

        self.canvas.axes.set_title('Динамика среднего срока до погашения по месяцам')
        self.canvas.axes.set_xlabel('Месяц')
        self.canvas.axes.set_ylabel('Срок (месяцы)')
        self.canvas.axes.set_xticks(months)
        self.canvas.axes.legend()
        self.canvas.axes.grid(True, alpha=0.3)

    def _plot_comparison(self):
        """Построение сравнительной диаграммы для разных сценариев"""
        # Для полноценного сравнения нужны результаты всех трех сценариев
        # Здесь используется текущий сценарий для демонстрации
        if self.current_solution:
            fun_value = self.current_solution.get('fun', 0)
            mode = self.current_solution.get('mode', 'basic')

            mode_names = {'basic': 'Без\nограничений', 'risk': 'С риском', 'full': 'Полный'}

            self.canvas.axes.bar([mode_names.get(mode, mode)], [fun_value],
                                 color='#45B7D1', alpha=0.7)
            self.canvas.axes.set_title('Сравнение начального фонда для текущего сценария')
            self.canvas.axes.set_ylabel('Начальный фонд (млн руб)')

            # Добавление подписи значения
            self.canvas.axes.text(0, fun_value, f'{fun_value:.1f}',
                                  ha='center', va='bottom')

        self.canvas.axes.grid(True, alpha=0.3)