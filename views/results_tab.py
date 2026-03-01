"""
Модуль вкладки отображения результатов
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pandas as pd
import traceback
import sys


class ResultsTab(QWidget):
    """
    Вкладка для отображения результатов оптимизации
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
        title_label = QLabel("Результаты оптимизации")
        title_label.setProperty("role", "heading")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Группа основных показателей
        summary_group = QGroupBox("📈 Основные показатели")
        summary_layout = QGridLayout()
        summary_layout.setVerticalSpacing(15)
        summary_layout.setHorizontalSpacing(20)

        # Карточка начального фонда
        self.fund_label = QLabel("—")
        self.fund_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1560BD;")
        self.fund_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Карточка доходности
        self.income_label = QLabel("—")
        self.income_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1560BD;")
        self.income_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Карточка количества инвестиций
        self.count_label = QLabel("—")
        self.count_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #1560BD;")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Карточка режима
        self.mode_label = QLabel("—")
        self.mode_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1560BD;")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        summary_layout.addWidget(QLabel("Начальный фонд:"), 0, 0)
        summary_layout.addWidget(self.fund_label, 0, 1)
        summary_layout.addWidget(QLabel("тыс. руб"), 0, 2)

        summary_layout.addWidget(QLabel("Общая доходность:"), 1, 0)
        summary_layout.addWidget(self.income_label, 1, 1)
        summary_layout.addWidget(QLabel("тыс. руб"), 1, 2)

        summary_layout.addWidget(QLabel("Количество инвестиций:"), 2, 0)
        summary_layout.addWidget(self.count_label, 2, 1)

        summary_layout.addWidget(QLabel("Режим расчета:"), 3, 0)
        summary_layout.addWidget(self.mode_label, 3, 1)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Группа распределения инвестиций
        allocation_group = QGroupBox("📊 Распределение инвестиций")
        allocation_layout = QVBoxLayout()

        self.allocation_table = QTableWidget()
        self.allocation_table.setColumnCount(5)
        self.allocation_table.setHorizontalHeaderLabels(
            ["Инструмент", "Месяц начала", "Сумма (тыс. руб)", "Доход (тыс. руб)", "Риск"]
        )
        self.allocation_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.allocation_table.setAlternatingRowColors(True)

        allocation_layout.addWidget(self.allocation_table)
        allocation_group.setLayout(allocation_layout)
        layout.addWidget(allocation_group)

        # Группа анализа ограничений
        constraints_group = QGroupBox("🔍 Анализ ограничений")
        constraints_layout = QVBoxLayout()

        self.constraints_text = QTextEdit()
        self.constraints_text.setReadOnly(True)
        self.constraints_text.setMaximumHeight(150)
        constraints_layout.addWidget(self.constraints_text)

        constraints_group.setLayout(constraints_layout)
        layout.addWidget(constraints_group)

        self.setLayout(layout)

    def display_results(self, solution: dict, constraints_df: pd.DataFrame, allocation_df: pd.DataFrame):
        """Отображение результатов"""
        try:
            print("\n=== DISPLAY RESULTS ===")
            self.current_solution = solution

            if not solution or not solution.get('success', False):
                print("Решение не успешно")
                self.fund_label.setText("—")
                self.income_label.setText("—")
                self.count_label.setText("—")
                self.mode_label.setText("—")
                self.constraints_text.setText(f"❌ Решение не найдено")
                self.allocation_table.setRowCount(0)
                return

            # ===== РАСЧЕТ НАЧАЛЬНОГО ФОНДА =====
            if solution.get('mode') == 'basic' and 'path' in solution:
                fund_value = solution['fun']
                path_info = f"✅ ВЫБРАН ПУТЬ: {solution['path']}\n"
                if 'details' in solution:
                    path_info += "Детали:\n"
                    for k, v in solution['details'].items():
                        path_info += f"  {k}: {v:.2f} тыс. руб\n"
            else:
                x = solution.get('x', [])
                fund_value = sum(x) if x is not None else 0
                path_info = ""

                if fund_value > 0:
                    path_info = f"💰 Всего инвестиций: {fund_value:.2f} тыс. руб\n"
                    variables = solution.get('variables', [])
                    month1_sum = sum(x[i] for i, var in enumerate(variables)
                                     if var['start_month'] == 1 and x[i] > 1e-3)
                    if month1_sum > 0:
                        path_info += f"   Из них в месяц 1: {month1_sum:.2f} тыс. руб\n"

            # УБИРАЕМ округление до тысяч
            self.fund_label.setText(f"{fund_value:.0f}".replace(',', ' '))
            print(f"fund_value = {fund_value:.2f} тыс. руб")

            # ===== ОБЩАЯ ДОХОДНОСТЬ =====
            total_income = solution.get('total_income', 0)
            if total_income is None:
                total_income = 0
            # УБИРАЕМ округление до тысяч
            self.income_label.setText(f"{total_income:.0f}".replace(',', ' '))

            # ===== КОЛИЧЕСТВО ИНВЕСТИЦИЙ =====
            allocation = solution.get('allocation', {})
            if allocation is None:
                allocation = {}
            self.count_label.setText(str(len(allocation)))

            # ===== РЕЖИМ РАСЧЕТА =====
            mode_names = {'basic': 'Без ограничений', 'risk': 'С риском', 'full': 'Полный'}
            mode = solution.get('mode', '')
            self.mode_label.setText(mode_names.get(mode, mode))

            # ===== ТАБЛИЦА РАСПРЕДЕЛЕНИЯ =====
            if allocation_df is not None and not allocation_df.empty:
                self.allocation_table.setRowCount(len(allocation_df))
                for i in range(len(allocation_df)):
                    row = allocation_df.iloc[i]

                    self.allocation_table.setItem(i, 0, QTableWidgetItem(str(row.get('Инструмент', ''))))
                    self.allocation_table.setItem(i, 1, QTableWidgetItem(str(row.get('Месяц начала', ''))))

                    # УБИРАЕМ форматирование с запятыми
                    amount = row.get('Сумма (тыс. руб)', '0')
                    if isinstance(amount, str):
                        amount = amount.replace(',', '')
                    self.allocation_table.setItem(i, 2, QTableWidgetItem(str(amount)))

                    income = row.get('Доход (тыс. руб)', '0')
                    if isinstance(income, str):
                        income = income.replace(',', '')
                    self.allocation_table.setItem(i, 3, QTableWidgetItem(str(income)))

                    self.allocation_table.setItem(i, 4, QTableWidgetItem(str(row.get('Риск', ''))))
            else:
                self.allocation_table.setRowCount(0)

            # ===== АНАЛИЗ ОГРАНИЧЕНИЙ =====
            if 'analysis_text' in solution:
                self.constraints_text.setText(solution['analysis_text'])
            elif constraints_df is not None and not constraints_df.empty:
                text = path_info
                if text:
                    text += "\n\n📊 Результаты проверки ограничений:\n\n"
                else:
                    text = "📊 Результаты проверки ограничений:\n\n"

                for _, row in constraints_df.iterrows():
                    risk_status = row.get('Риск статус', '')
                    dur_status = row.get('Срок статус', '')

                    risk_emoji = "✅" if risk_status == 'OK' else "❌"
                    dur_emoji = "✅" if dur_status == 'OK' else "❌"

                    month = int(row.get('Месяц', 0))
                    risk_fact = row.get('Риск факт', 0)
                    risk_limit = row.get('Риск лимит', 6)
                    dur_fact = row.get('Срок факт', 0)
                    dur_limit = row.get('Срок лимит', 2.5)
                    assets = row.get('Активы (тыс. руб)', 0)

                    text += f"Месяц {month}: "
                    text += f"{risk_emoji} риск = {risk_fact:.2f} (лимит {risk_limit:.1f}), "
                    text += f"{dur_emoji} срок = {dur_fact:.2f} (лимит {dur_limit:.1f}), "
                    text += f"активы = {assets:.2f} тыс. руб\n"

                self.constraints_text.setText(text)
            else:
                if path_info:
                    self.constraints_text.setText(path_info)
                else:
                    self.constraints_text.setText("Нет данных для анализа")

            print("=== DISPLAY RESULTS FINISHED ===\n")

        except Exception as e:
            print(f"❌ ОШИБКА В DISPLAY_RESULTS: {e}")
            traceback.print_exc()
            self.constraints_text.setText(f"Ошибка отображения: {str(e)}")

    def clear(self):
        """Очистка результатов"""
        self.fund_label.setText("—")
        self.income_label.setText("—")
        self.count_label.setText("—")
        self.mode_label.setText("—")
        self.allocation_table.setRowCount(0)
        self.constraints_text.clear()
        self.current_solution = None