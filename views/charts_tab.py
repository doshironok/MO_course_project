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
    """Виджет для отображения графиков matplotlib (уменьшенный размер)"""

    def __init__(self, parent=None, width=8, height=4.5, dpi=90):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=COLORS.get('background', '#1e1e2e'))
        self.fig.patch.set_facecolor(COLORS.get('background', '#1e1e2e'))
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor(COLORS.get('surface', '#2d2d3d'))
        super().__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout(pad=1.5)


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
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title_label = QLabel("Визуализация результатов")
        title_label.setProperty("role", "heading")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Панель управления
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.get('surface', '#2d2d3d')};
                border: 1px solid {COLORS.get('border', '#3d3d4d')};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(10)

        control_layout.addWidget(QLabel("📊 Тип графика:"))

        self.chart_combo = QComboBox()
        self.chart_combo.addItems([
            "Структура портфеля",
            "Динамика риска",
            "Динамика срока",
            "Сравнение сценариев"
        ])
        self.chart_combo.setMinimumWidth(180)
        self.chart_combo.currentIndexChanged.connect(self.update_chart)
        control_layout.addWidget(self.chart_combo)

        control_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setProperty("class", "secondary")
        self.refresh_btn.setMaximumWidth(100)
        self.refresh_btn.clicked.connect(self.update_chart)
        control_layout.addWidget(self.refresh_btn)

        layout.addWidget(control_frame)

        # Область графика
        self.canvas = MplCanvas(self, width=8, height=4.5, dpi=90)
        layout.addWidget(self.canvas)

        # Статус
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.get('secondary', '#1a1a2a')};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self.status_label = QLabel("Выберите тип графика")
        self.status_label.setStyleSheet(f"color: {COLORS.get('text_light', '#a0a0b0')}; font-size: 11px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        self.setLayout(layout)

    def set_solution(self, solution: dict):
        """Установка решения для визуализации"""
        self.current_solution = solution
        # Вычисляем динамику риска и срока из данных решения
        self._calculate_monthly_metrics()
        self.update_chart()

    def _calculate_monthly_metrics(self):
        """Вычисление помесячных значений риска и срока на основе активных инвестиций"""
        if not self.current_solution or not self.current_solution.get('success', False):
            self.current_solution['monthly_risk'] = [0] * 6
            self.current_solution['monthly_duration'] = [0] * 6
            return

        allocation = self.current_solution.get('allocation', {})

        # Данные по инструментам (риск, срок, месяц старта, месяц возврата)
        # Инструмент: (риск, срок_месяцев)
        instrument_data = {
            'A': {'risk': 2, 'duration': 1},
            'B': {'risk': 6, 'duration': 2},
            'C': {'risk': 9, 'duration': 3},
            'O': {'risk': 10, 'duration': 6}
        }

        # Месяцы 1-6 (для каждого месяца определяем активные инвестиции)
        monthly_risk = []
        monthly_duration = []

        for month in range(1, 7):
            total_amount = 0
            weighted_risk = 0
            weighted_duration = 0

            for key, alloc in allocation.items():
                instrument = alloc.get('instrument', '')
                amount = alloc.get('amount', 0)
                start_month = alloc.get('start_month', 0)

                if amount <= 0 or not instrument:
                    continue

                # Определяем месяц возврата в зависимости от инструмента
                if instrument == 'A':
                    return_month = start_month + 1
                    risk = 2
                    dur = 1
                elif instrument == 'B':
                    return_month = start_month + 2
                    risk = 6
                    dur = 2
                elif instrument == 'C':
                    return_month = start_month + 3
                    risk = 9
                    dur = 3
                elif instrument == 'O':
                    return_month = start_month + 6
                    risk = 10
                    dur = 6
                else:
                    continue

                # Инвестиция активна в данном месяце, если месяц между start_month и return_month-1
                if start_month <= month < return_month:
                    total_amount += amount
                    weighted_risk += risk * amount
                    # Оставшийся срок до погашения
                    remaining = return_month - month
                    weighted_duration += remaining * amount

            if total_amount > 0:
                monthly_risk.append(weighted_risk / total_amount)
                monthly_duration.append(weighted_duration / total_amount)
            else:
                monthly_risk.append(0)
                monthly_duration.append(0)

        self.current_solution['monthly_risk'] = monthly_risk
        self.current_solution['monthly_duration'] = monthly_duration

        # Добавляем лимиты
        if 'risk_limit' not in self.current_solution:
            self.current_solution['risk_limit'] = 6
        if 'duration_limit' not in self.current_solution:
            self.current_solution['duration_limit'] = 2.5

    def update_chart(self):
        """Обновление графика в соответствии с выбранным типом"""
        if not self.current_solution or not self.current_solution.get('success', False):
            self.status_label.setText("❌ Нет данных")
            self._show_no_data_message()
            return

        chart_type = self.chart_combo.currentIndex()

        try:
            self.canvas.axes.clear()
            self._setup_axes_style()

            if chart_type == 0:
                self._plot_structure()
            elif chart_type == 1:
                self._plot_risk_dynamics()
            elif chart_type == 2:
                self._plot_duration_dynamics()
            elif chart_type == 3:
                self._plot_comparison()

            self.canvas.fig.tight_layout(pad=1.2)
            self.canvas.draw()
            self.status_label.setText(f"✓ {self.chart_combo.currentText()}")

        except Exception as e:
            self.status_label.setText(f"❌ Ошибка: {str(e)[:30]}")
            self._show_error_message(str(e))

    def _setup_axes_style(self):
        """Настройка стиля осей"""
        self.canvas.axes.tick_params(colors=COLORS.get('text', '#ffffff'), labelsize=9)
        for spine in self.canvas.axes.spines.values():
            spine.set_color(COLORS.get('border', '#3d3d4d'))
            spine.set_linewidth(0.5)

    def _show_no_data_message(self):
        """Показать сообщение об отсутствии данных"""
        self.canvas.axes.clear()
        self.canvas.axes.text(0.5, 0.5, 'Нет данных',
                             ha='center', va='center', fontsize=11,
                             color=COLORS.get('text_light', '#a0a0b0'),
                             transform=self.canvas.axes.transAxes)
        self.canvas.axes.set_xticks([])
        self.canvas.axes.set_yticks([])
        for spine in self.canvas.axes.spines.values():
            spine.set_visible(False)
        self.canvas.draw()

    def _show_error_message(self, error_msg):
        """Показать сообщение об ошибке"""
        self.canvas.axes.clear()
        self.canvas.axes.text(0.5, 0.5, f'Ошибка',
                             ha='center', va='center', fontsize=11,
                             color='red', transform=self.canvas.axes.transAxes)
        self.canvas.axes.set_xticks([])
        self.canvas.axes.set_yticks([])
        self.canvas.draw()

    def _plot_structure(self):
        """Построение графика структуры портфеля"""
        allocation = self.current_solution.get('allocation', {})

        instruments = {}
        for key, alloc in allocation.items():
            instr = alloc.get('instrument', 'Unknown')
            amount = alloc.get('amount', 0)
            if instr not in instruments:
                instruments[instr] = 0
            instruments[instr] += amount

        if not instruments:
            self.canvas.axes.text(0.5, 0.5, "Нет данных",
                                 ha='center', va='center', transform=self.canvas.axes.transAxes)
            return

        names = list(instruments.keys())
        values = list(instruments.values())

        colors = [COLORS.get('primary', '#4A90D9'),
                  COLORS.get('primary_light', '#6CA8E8'),
                  '#4A7DB5', '#6C8EB5']

        bars = self.canvas.axes.bar(names, values, color=colors[:len(names)],
                                    edgecolor=COLORS.get('border', '#3d3d4d'), linewidth=1)

        self.canvas.axes.set_title('Структура портфеля', fontsize=11, fontweight='bold',
                                   color=COLORS.get('primary', '#4A90D9'))
        self.canvas.axes.set_xlabel('Инструмент', fontsize=9, color=COLORS.get('text', '#ffffff'))
        self.canvas.axes.set_ylabel('Сумма (млн руб)', fontsize=9, color=COLORS.get('text', '#ffffff'))

        for bar in bars:
            height = bar.get_height()
            if height > 0:
                self.canvas.axes.text(bar.get_x() + bar.get_width() / 2., height,
                                      f'{height:.1f}',
                                      ha='center', va='bottom', fontsize=8,
                                      fontweight='bold', color=COLORS.get('primary', '#4A90D9'))

        self.canvas.axes.tick_params(axis='x', rotation=45, labelsize=8)
        self.canvas.axes.grid(True, alpha=0.3, axis='y', color=COLORS.get('border', '#3d3d4d'))

    def _plot_risk_dynamics(self):
        """Построение графика динамики риска"""
        monthly_risk = self.current_solution.get('monthly_risk', [])
        risk_limit = self.current_solution.get('risk_limit', 6)

        if not monthly_risk:
            monthly_risk = [0] * 6

        months = list(range(1, min(len(monthly_risk), 7) + 1))
        risk_data = monthly_risk[:6]

        self.canvas.axes.plot(months, risk_data, 'o-', linewidth=2, markersize=6,
                             label='Фактический риск', color=COLORS.get('primary', '#4A90D9'),
                             markerfacecolor='white', markeredgewidth=1.5)

        self.canvas.axes.axhline(y=risk_limit, color=COLORS.get('error', '#E74C3C'),
                                linestyle='--', linewidth=1.5, label=f'Лимит ({risk_limit})')

        # Подсветка превышений
        for i, (month, risk) in enumerate(zip(months, risk_data)):
            if risk > risk_limit:
                self.canvas.axes.fill_between([month-0.2, month+0.2], risk_limit, risk,
                                             color=COLORS.get('error', '#E74C3C'), alpha=0.3)

        self.canvas.axes.set_title('Динамика риска', fontsize=11, fontweight='bold',
                                  color=COLORS.get('primary', '#4A90D9'))
        self.canvas.axes.set_xlabel('Месяц', fontsize=9, color=COLORS.get('text', '#ffffff'))
        self.canvas.axes.set_ylabel('Риск', fontsize=9, color=COLORS.get('text', '#ffffff'))
        self.canvas.axes.set_xticks(months)
        self.canvas.axes.set_ylim(bottom=0, top=max(max(risk_data), risk_limit) * 1.1)
        self.canvas.axes.legend(loc='upper right', fontsize=8, framealpha=0.9,
                               facecolor=COLORS.get('surface', '#2d2d3d'))
        self.canvas.axes.grid(True, alpha=0.3, color=COLORS.get('border', '#3d3d4d'))

    def _plot_duration_dynamics(self):
        """Построение графика динамики срока погашения"""
        monthly_duration = self.current_solution.get('monthly_duration', [])
        duration_limit = self.current_solution.get('duration_limit', 2.5)

        if not monthly_duration:
            monthly_duration = [0] * 6

        months = list(range(1, min(len(monthly_duration), 7) + 1))
        duration_data = monthly_duration[:6]

        self.canvas.axes.plot(months, duration_data, 's-', linewidth=2, markersize=6,
                             label='Фактический срок', color=COLORS.get('primary_light', '#6CA8E8'),
                             markerfacecolor='white', markeredgewidth=1.5)

        self.canvas.axes.axhline(y=duration_limit, color=COLORS.get('error', '#E74C3C'),
                                linestyle='--', linewidth=1.5, label=f'Лимит ({duration_limit})')

        # Подсветка превышений
        for i, (month, duration) in enumerate(zip(months, duration_data)):
            if duration > duration_limit:
                self.canvas.axes.fill_between([month-0.2, month+0.2], duration_limit, duration,
                                             color=COLORS.get('error', '#E74C3C'), alpha=0.3)

        self.canvas.axes.set_title('Динамика срока погашения', fontsize=11, fontweight='bold',
                                  color=COLORS.get('primary', '#4A90D9'))
        self.canvas.axes.set_xlabel('Месяц', fontsize=9, color=COLORS.get('text', '#ffffff'))
        self.canvas.axes.set_ylabel('Срок (мес)', fontsize=9, color=COLORS.get('text', '#ffffff'))
        self.canvas.axes.set_xticks(months)
        self.canvas.axes.set_ylim(bottom=0, top=max(max(duration_data), duration_limit) * 1.1)
        self.canvas.axes.legend(loc='upper right', fontsize=8, framealpha=0.9,
                               facecolor=COLORS.get('surface', '#2d2d3d'))
        self.canvas.axes.grid(True, alpha=0.3, color=COLORS.get('border', '#3d3d4d'))

    def _plot_comparison(self):
        """Построение сравнительной диаграммы"""
        fun_value = self.current_solution.get('fun', 0)
        mode = self.current_solution.get('mode', 'basic')

        mode_names = {'basic': 'Без\nограничений', 'risk': 'С\nриском', 'full': 'Полный'}
        mode_display = mode_names.get(mode, mode)

        colors = [COLORS.get('primary', '#4A90D9')]

        bars = self.canvas.axes.bar([mode_display], [fun_value],
                                    color=colors[0], alpha=0.8,
                                    edgecolor=COLORS.get('border', '#3d3d4d'), linewidth=1.5)

        self.canvas.axes.set_title('Начальный фонд', fontsize=11, fontweight='bold',
                                   color=COLORS.get('primary', '#4A90D9'))
        self.canvas.axes.set_ylabel('Фонд (млн руб)', fontsize=9, color=COLORS.get('text', '#ffffff'))

        for bar in bars:
            height = bar.get_height()
            if height > 0:
                self.canvas.axes.text(bar.get_x() + bar.get_width() / 2., height,
                                      f'{height:.2f}',
                                      ha='center', va='bottom', fontsize=9,
                                      fontweight='bold', color=COLORS.get('primary', '#4A90D9'))

        self.canvas.axes.grid(True, alpha=0.3, axis='y', color=COLORS.get('border', '#3d3d4d'))