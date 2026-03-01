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

    def format_thousands(self, value):
        """Форматирование числа с разделителями разрядов"""
        try:
            if value is None:
                return "0"
            # Преобразуем в число и округляем до целых
            num_value = float(value)
            # Не делим на 1000, только форматируем с пробелами
            return f"{int(round(num_value)):,}".replace(",", " ")
        except (ValueError, TypeError):
            return str(value)

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

            # Определяем режим расчета
            mode = solution.get('mode', '')

            # ===== РАСЧЕТ НАЧАЛЬНОГО ФОНДА =====
            if mode == 'basic' and 'path' in solution:
                # Для basic режима - значение в рублях, нужно преобразовать в тысячи
                fund_value = solution.get('fun', 0)
                if fund_value is None:
                    fund_value = 0

                # Делим на 1000 для отображения в тысячах рублей
                fund_value_thousands = fund_value / 1000

                path_info = f"✅ ВЫБРАН ПУТЬ: {solution['path']}\n"
                if 'details' in solution:
                    path_info += "Детали:\n"
                    for k, v in solution['details'].items():
                        # Детали тоже в рублях, делим на 1000
                        v_thousands = v / 1000
                        path_info += f"  {k}: {self.format_thousands(v_thousands)} тыс. руб\n"

                self.fund_label.setText(self.format_thousands(fund_value_thousands))
                print(f"fund_value (basic) = {fund_value:.2f} руб = {self.format_thousands(fund_value_thousands)} тыс. руб")

            else:
                # Для risk и full режимов - значения уже в тысячах рублей
                x = solution.get('x', [])
                fund_value = sum(x) if x is not None else 0
                path_info = ""

                if fund_value > 0:
                    # Не делим на 1000, так как уже в тысячах
                    self.fund_label.setText(self.format_thousands(fund_value))

                    path_info = f"💰 Всего инвестиций: {self.format_thousands(fund_value)} тыс. руб\n"
                    variables = solution.get('variables', [])
                    month1_sum = sum(x[i] for i, var in enumerate(variables)
                                     if var['start_month'] == 1 and x[i] > 1e-3)
                    if month1_sum > 0:
                        path_info += f"   Из них в месяц 1: {self.format_thousands(month1_sum)} тыс. руб\n"

                    print(f"fund_value (risk/full) = {fund_value:.2f} тыс. руб")

            # ===== ОБЩАЯ ДОХОДНОСТЬ =====
            total_income = solution.get('total_income', 0)
            if total_income is None:
                total_income = 0

            # Для basic режима total_income в рублях, для других - в тысячах
            if mode == 'basic':
                total_income_thousands = total_income / 1000
                self.income_label.setText(self.format_thousands(total_income_thousands))
                print(f"total_income (basic) = {total_income:.2f} руб = {self.format_thousands(total_income_thousands)} тыс. руб")
            else:
                self.income_label.setText(self.format_thousands(total_income))
                print(f"total_income (risk/full) = {total_income:.2f} тыс. руб")

            # ===== КОЛИЧЕСТВО ИНВЕСТИЦИЙ =====
            allocation = solution.get('allocation', {})
            if allocation is None:
                allocation = {}
            self.count_label.setText(str(len(allocation)))

            # ===== РЕЖИМ РАСЧЕТА =====
            mode_names = {'basic': 'Без ограничений', 'risk': 'С риском', 'full': 'Полный'}
            self.mode_label.setText(mode_names.get(mode, mode))

            # ===== ТАБЛИЦА РАСПРЕДЕЛЕНИЯ =====
            if allocation_df is not None and not allocation_df.empty:
                self.allocation_table.setRowCount(len(allocation_df))
                for i in range(len(allocation_df)):
                    row = allocation_df.iloc[i]

                    self.allocation_table.setItem(i, 0, QTableWidgetItem(str(row.get('Инструмент', ''))))
                    self.allocation_table.setItem(i, 1, QTableWidgetItem(str(row.get('Месяц начала', ''))))

                    # Сумма
                    amount = row.get('Сумма (тыс. руб)', '0')
                    if isinstance(amount, (int, float)):
                        # Для basic режима данные могут быть в рублях
                        if mode == 'basic':
                            amount = amount / 1000
                        amount = self.format_thousands(amount)
                    elif isinstance(amount, str) and amount.replace('.', '').replace('-', '').isdigit():
                        try:
                            amount_num = float(amount)
                            if mode == 'basic':
                                amount_num = amount_num / 1000
                            amount = self.format_thousands(amount_num)
                        except ValueError:
                            pass
                    self.allocation_table.setItem(i, 2, QTableWidgetItem(str(amount)))

                    # Доход
                    income = row.get('Доход (тыс. руб)', '0')
                    if isinstance(income, (int, float)):
                        if mode == 'basic':
                            income = income / 1000
                        income = self.format_thousands(income)
                    elif isinstance(income, str) and income.replace('.', '').replace('-', '').isdigit():
                        try:
                            income_num = float(income)
                            if mode == 'basic':
                                income_num = income_num / 1000
                            income = self.format_thousands(income_num)
                        except ValueError:
                            pass
                    self.allocation_table.setItem(i, 3, QTableWidgetItem(str(income)))

                    self.allocation_table.setItem(i, 4, QTableWidgetItem(str(row.get('Риск', ''))))
            else:
                self.allocation_table.setRowCount(0)

            # ===== АНАЛИЗ ОГРАНИЧЕНИЙ =====
            if 'analysis_text' in solution:
                self.constraints_text.setText(solution['analysis_text'])
            elif constraints_df is not None and not constraints_df.empty:
                text = path_info if 'path_info' in locals() else ""
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

                    # Активы
                    if isinstance(assets, (int, float)):
                        if mode == 'basic':
                            assets = assets / 1000
                        assets_display = self.format_thousands(assets)
                    else:
                        assets_display = str(assets)

                    text += f"Месяц {month}: "
                    text += f"{risk_emoji} риск = {risk_fact:.2f} (лимит {risk_limit:.1f}), "
                    text += f"{dur_emoji} срок = {dur_fact:.2f} (лимит {dur_limit:.1f}), "
                    text += f"активы = {assets_display} тыс. руб\n"

                self.constraints_text.setText(text)
            else:
                if 'path_info' in locals() and path_info:
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