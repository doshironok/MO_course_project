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
        summary_layout.addWidget(QLabel("млн. руб"), 0, 2)

        summary_layout.addWidget(QLabel("Общая доходность:"), 1, 0)
        summary_layout.addWidget(self.income_label, 1, 1)
        summary_layout.addWidget(QLabel("млн. руб"), 1, 2)

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
            ["Инструмент", "Месяц начала", "Сумма (млн руб)", "Доход (млн руб)", "Риск"]
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

    def format_millions(self, value):
        """Форматирование числа в млн руб"""
        try:
            if value is None:
                return "0.00"
            # Если value строка, пробуем преобразовать
            if isinstance(value, str):
                # Убираем пробелы и заменяем запятую на точку
                cleaned = value.replace(' ', '').replace(',', '.')
                num_value = float(cleaned)
            else:
                num_value = float(value)
            # Форматируем с двумя знаками после запятой и пробелами для разделения тысяч
            return f"{num_value:,.2f}".replace(",", " ")
        except (ValueError, TypeError) as e:
            print(f"format_millions error: {e}, value={value}")
            return str(value)

    def display_results(self, solution: dict, constraints_df: pd.DataFrame, allocation_df: pd.DataFrame):
        """Отображение результатов"""
        try:
            print("\n=== DISPLAY RESULTS ===")
            print(f"allocation_df columns: {allocation_df.columns.tolist() if allocation_df is not None else 'None'}")
            print(f"allocation_df head:\n{allocation_df.head() if allocation_df is not None else 'None'}")

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

            mode = solution.get('mode', '')

            # ===== НАЧАЛЬНЫЙ ФОНД =====
            fund_value = solution.get('fun', 0)
            if fund_value is None:
                fund_value = 0

            self.fund_label.setText(self.format_millions(fund_value))
            print(f"fund_value = {fund_value:.2f} млн руб")

            # ===== ОБЩАЯ ДОХОДНОСТЬ =====
            total_income = solution.get('total_income', 0)
            if total_income is None:
                total_income = 0
            self.income_label.setText(self.format_millions(total_income))
            print(f"total_income = {total_income:.2f} млн руб")

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
                # Определяем названия колонок
                col_instrument = None
                col_month = None
                col_amount = None
                col_income = None
                col_risk = None

                for col in allocation_df.columns:
                    if 'инструмент' in col.lower() or 'instrument' in col.lower():
                        col_instrument = col
                    elif 'месяц' in col.lower() or 'month' in col.lower():
                        col_month = col
                    elif 'сумма' in col.lower() or 'amount' in col.lower():
                        col_amount = col
                    elif 'доход' in col.lower() or 'income' in col.lower():
                        col_income = col
                    elif 'риск' in col.lower() or 'risk' in col.lower():
                        col_risk = col

                print(
                    f"Found columns: instrument={col_instrument}, month={col_month}, amount={col_amount}, income={col_income}, risk={col_risk}")

                self.allocation_table.setRowCount(len(allocation_df))
                for i in range(len(allocation_df)):
                    row = allocation_df.iloc[i]

                    # Инструмент
                    if col_instrument:
                        self.allocation_table.setItem(i, 0, QTableWidgetItem(str(row.get(col_instrument, ''))))
                    else:
                        self.allocation_table.setItem(i, 0, QTableWidgetItem(str(row.get('Инструмент', ''))))

                    # Месяц начала
                    if col_month:
                        self.allocation_table.setItem(i, 1, QTableWidgetItem(str(row.get(col_month, ''))))
                    else:
                        self.allocation_table.setItem(i, 1, QTableWidgetItem(str(row.get('Месяц начала', ''))))

                    # Сумма
                    amount_value = 0
                    if col_amount:
                        amount_value = row.get(col_amount, 0)
                    else:
                        # Пробуем разные варианты
                        if 'Сумма (млн руб)' in row.index:
                            amount_value = row.get('Сумма (млн руб)', 0)
                        elif 'Сумма (млн руб)' in row.index:
                            amount_value = row.get('Сумма (млн руб)', 0) / 1000
                        elif 'Сумма' in row.index:
                            amount_value = row.get('Сумма', 0)
                        else:
                            amount_value = 0

                    # Если значение строка, пробуем преобразовать
                    if isinstance(amount_value, str):
                        try:
                            amount_value = float(amount_value.replace(',', '.').replace(' ', ''))
                        except:
                            amount_value = 0

                    self.allocation_table.setItem(i, 2, QTableWidgetItem(self.format_millions(amount_value)))

                    # Доход
                    income_value = 0
                    if col_income:
                        income_value = row.get(col_income, 0)
                    else:
                        # Пробуем разные варианты
                        if 'Доход (млн руб)' in row.index:
                            income_value = row.get('Доход (млн руб)', 0)
                        elif 'Доход (млн руб)' in row.index:
                            income_value = row.get('Доход (млн руб)', 0) / 1000
                        elif 'Доход' in row.index:
                            income_value = row.get('Доход', 0)
                        else:
                            income_value = 0

                    if isinstance(income_value, str):
                        try:
                            income_value = float(income_value.replace(',', '.').replace(' ', ''))
                        except:
                            income_value = 0

                    self.allocation_table.setItem(i, 3, QTableWidgetItem(self.format_millions(income_value)))

                    # Риск
                    if col_risk:
                        self.allocation_table.setItem(i, 4, QTableWidgetItem(str(row.get(col_risk, ''))))
                    else:
                        self.allocation_table.setItem(i, 4, QTableWidgetItem(str(row.get('Риск', ''))))
            else:
                self.allocation_table.setRowCount(0)
                print("allocation_df is empty or None")

            # ===== АНАЛИЗ ОГРАНИЧЕНИЙ =====
            if 'analysis_text' in solution:
                self.constraints_text.setText(solution['analysis_text'])
            elif constraints_df is not None and not constraints_df.empty:
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

                    # Ищем активы в разных колонках
                    assets = 0
                    if 'Активы (млн руб)' in row.index:
                        assets = row.get('Активы (млн руб)', 0)
                    elif 'Активы (тыс. руб)' in row.index:
                        assets = row.get('Активы (тыс. руб)', 0) / 1000
                    elif 'Активы' in row.index:
                        assets = row.get('Активы', 0)
                    else:
                        assets = 0

                    text += f"Месяц {month}: "
                    text += f"{risk_emoji} риск = {risk_fact:.2f} (лимит {risk_limit:.1f}), "
                    text += f"{dur_emoji} срок = {dur_fact:.2f} (лимит {dur_limit:.1f}), "
                    text += f"активы = {self.format_millions(assets)} млн руб\n"

                self.constraints_text.setText(text)
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