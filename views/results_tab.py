"""
Модуль вкладки отображения результатов
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pandas as pd
import traceback
import numpy as np


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
        # Главный layout с прокруткой
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Область прокрутки
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Содержимое
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
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
        summary_layout.addWidget(QLabel("млн руб"), 0, 2)

        summary_layout.addWidget(QLabel("Общая доходность:"), 1, 0)
        summary_layout.addWidget(self.income_label, 1, 1)
        summary_layout.addWidget(QLabel("млн руб"), 1, 2)

        summary_layout.addWidget(QLabel("Количество инвестиций:"), 2, 0)
        summary_layout.addWidget(self.count_label, 2, 1)

        summary_layout.addWidget(QLabel("Режим расчета:"), 3, 0)
        summary_layout.addWidget(self.mode_label, 3, 1)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Группа распределения инвестиций - УВЕЛИЧЕННАЯ
        allocation_group = QGroupBox("📊 Распределение инвестиций")
        allocation_layout = QVBoxLayout()

        # Таблица с прокруткой
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setMinimumHeight(250)  # Увеличенная минимальная высота
        table_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #D5DCE5;
                border-radius: 4px;
                background-color: white;
            }
        """)

        self.allocation_table = QTableWidget()
        self.allocation_table.setColumnCount(5)
        self.allocation_table.setHorizontalHeaderLabels(
            ["Инструмент", "Месяц начала", "Сумма (млн руб)", "Доход (млн руб)", "Риск"]
        )
        self.allocation_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.allocation_table.setAlternatingRowColors(True)
        self.allocation_table.verticalHeader().setDefaultSectionSize(35)  # Высота строк
        self.allocation_table.setStyleSheet("""
            QTableWidget {
                font-size: 11pt;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #F0F4FA;
                padding: 10px;
                font-weight: bold;
                font-size: 11pt;
            }
        """)

        table_scroll.setWidget(self.allocation_table)
        allocation_layout.addWidget(table_scroll)

        allocation_group.setLayout(allocation_layout)
        layout.addWidget(allocation_group, 1)  # Растягиваем по вертикали

        # Группа анализа ограничений и симплекс-метода
        analysis_group = QGroupBox("🔍 Анализ ограничений и симплекс-метод")
        analysis_layout = QVBoxLayout()

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMinimumHeight(300)  # Увеличенная высота
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                background-color: #F8FAFE;
                border: 1px solid #D5DCE5;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        analysis_layout.addWidget(self.analysis_text)

        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group, 1)  # Растягиваем по вертикали

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def format_millions(self, value):
        """Форматирование числа в млн руб"""
        try:
            if value is None:
                return "0.00"
            if isinstance(value, str):
                cleaned = value.replace(' ', '').replace(',', '.')
                num_value = float(cleaned)
            else:
                num_value = float(value)
            return f"{num_value:,.2f}".replace(",", " ")
        except (ValueError, TypeError) as e:
            print(f"format_millions error: {e}, value={value}")
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
                self.analysis_text.setText(f"❌ Решение не найдено\n\n{solution.get('message', '') if solution else ''}")
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
            mode_names = {'basic': 'BASIC (без ограничений)', 'risk': 'RISK (с риском)', 'full': 'FULL (полный)'}
            self.mode_label.setText(mode_names.get(mode, mode.upper()))

            # ===== ТАБЛИЦА РАСПРЕДЕЛЕНИЯ =====
            if allocation_df is not None and not allocation_df.empty:
                self.allocation_table.setRowCount(len(allocation_df))

                for i in range(len(allocation_df)):
                    row = allocation_df.iloc[i]

                    # Инструмент
                    instr = row.get('Инструмент', '')
                    item = QTableWidgetItem(str(instr))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.allocation_table.setItem(i, 0, item)

                    # Месяц начала
                    month = row.get('Месяц начала', '')
                    item = QTableWidgetItem(str(month))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.allocation_table.setItem(i, 1, item)

                    # Сумма
                    amount = row.get('Сумма (млн руб)', 0)
                    item = QTableWidgetItem(self.format_millions(amount))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.allocation_table.setItem(i, 2, item)

                    # Доход
                    income = row.get('Доход (млн руб)', 0)
                    item = QTableWidgetItem(self.format_millions(income))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.allocation_table.setItem(i, 3, item)

                    # Риск
                    risk = row.get('Риск', '')
                    item = QTableWidgetItem(str(risk))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.allocation_table.setItem(i, 4, item)

                # Автоматическая подгонка высоты строк
                self.allocation_table.resizeRowsToContents()
            else:
                self.allocation_table.setRowCount(0)
                print("allocation_df is empty or None")

            # ===== АНАЛИЗ ОГРАНИЧЕНИЙ И СИМПЛЕКС-МЕТОД =====
            self._generate_analysis_text(solution, constraints_df)

            print("=== DISPLAY RESULTS FINISHED ===\n")

        except Exception as e:
            print(f"❌ ОШИБКА В DISPLAY_RESULTS: {e}")
            traceback.print_exc()
            self.analysis_text.setText(f"Ошибка отображения: {str(e)}")

    def _generate_analysis_text(self, solution: dict, constraints_df: pd.DataFrame):
        """Генерация текста анализа с информацией о симплекс-методе"""
        text = ""

        # Заголовок
        mode = solution.get('mode', '')
        mode_names = {'basic': 'BASIC (без ограничений)', 'risk': 'RISK (с учетом риска)', 'full': 'FULL (полный)'}
        text += f"📊 РЕЗУЛЬТАТЫ РАСЧЕТА В РЕЖИМЕ {mode_names.get(mode, mode.upper())}\n"
        text += "=" * 70 + "\n\n"

        # Основные показатели
        fund_value = solution.get('fun', 0)
        total_income = solution.get('total_income', 0)
        text += f"💰 Начальный фонд: {self.format_millions(fund_value)} млн руб\n"
        text += f"📈 Общая доходность: {self.format_millions(total_income)} млн руб\n"

        # Эффективность
        if fund_value > 0:
            roi = (total_income / fund_value) * 100
            text += f"📊 Рентабельность: {roi:.2f}%\n\n"
        else:
            text += "\n"

        # Проверка ограничений
        text += "🔍 ПРОВЕРКА ОГРАНИЧЕНИЙ\n"
        text += "-" * 50 + "\n"

        if constraints_df is not None and not constraints_df.empty:
            violations_risk = []
            violations_dur = []

            for _, row in constraints_df.iterrows():
                month = int(row.get('Месяц', 0))
                risk_fact = row.get('Риск факт', 0)
                risk_limit = row.get('Риск лимит', 6)
                risk_status = row.get('Риск статус', '')
                dur_fact = row.get('Срок факт', 0)
                dur_limit = row.get('Срок лимит', 2.5)
                dur_status = row.get('Срок статус', '')
                assets = row.get('Активы (млн руб)', 0)

                risk_emoji = "✅" if risk_status == 'OK' else "❌"
                dur_emoji = "✅" if dur_status == 'OK' else "❌"

                text += f"Месяц {month}: {risk_emoji} риск = {risk_fact:.2f} (лимит {risk_limit:.1f}), "
                text += f"{dur_emoji} срок = {dur_fact:.2f} (лимит {dur_limit:.1f}), "
                text += f"активы = {self.format_millions(assets)} млн руб\n"

                if risk_status == 'НАРУШЕНИЕ':
                    violations_risk.append(str(month))
                if dur_status == 'НАРУШЕНИЕ':
                    violations_dur.append(str(month))

            if violations_risk:
                text += f"\n⚠️ Нарушения по риску в месяцах: {', '.join(violations_risk)}\n"
            if violations_dur:
                text += f"⚠️ Нарушения по сроку в месяцах: {', '.join(violations_dur)}\n"
        else:
            text += "Нет данных для проверки ограничений\n"

        # Информация о симплекс-методе
        text += "\n📐 СИМПЛЕКС-МЕТОД\n"
        text += "-" * 50 + "\n"

        simplex_iterations = solution.get('simplex_iterations', [])
        if simplex_iterations:
            phase1_iterations = [it for it in simplex_iterations if it.get('phase') == 1]
            phase2_iterations = [it for it in simplex_iterations if it.get('phase') == 2]

            text += f"• Фаза 1 (поиск допустимого базиса): {len(phase1_iterations)} итераций\n"
            text += f"• Фаза 2 (оптимизация): {len(phase2_iterations)} итераций\n"
            text += f"• Всего итераций: {len(simplex_iterations)}\n"

            # Детализация по итерациям Фазы 1
            if phase1_iterations:
                text += "\n  Фаза 1:\n"
                for it in phase1_iterations:
                    iter_num = it.get('iteration', 0)
                    entering = it.get('entering', '')
                    leaving = it.get('leaving', '')
                    obj = it.get('objective_value', 0)
                    if iter_num == 0:
                        text += f"    Начало: W = {obj:.4f}\n"
                    else:
                        text += f"    Итер. {iter_num}: ввод {entering}, вывод {leaving}, W = {obj:.4f}\n"

            # Детализация по итерациям Фазы 2
            if phase2_iterations:
                text += "\n  Фаза 2:\n"
                for it in phase2_iterations:
                    iter_num = it.get('iteration', 0)
                    entering = it.get('entering', '')
                    leaving = it.get('leaving', '')
                    obj = it.get('objective_value', 0)
                    if iter_num == 0:
                        text += f"    Начало: F = {abs(obj):.4f}\n"
                    else:
                        text += f"    Итер. {iter_num}: ввод {entering}, вывод {leaving}, F = {abs(obj):.4f}\n"

            # Оптимальное значение
            if phase2_iterations:
                last_iter = phase2_iterations[-1]
                obj_value = last_iter.get('objective_value')
                if obj_value is not None:
                    text += f"\n  ✅ Оптимальное значение F = {abs(obj_value):.4f} млн руб\n"

            text += "\n💡 Подробное пошаговое решение с симплекс-таблицами доступно на вкладке «Симплекс-метод»\n"
        else:
            text += "• Данные о симплекс-итерациях отсутствуют\n"
            text += "• Решение получено через scipy.linprog\n"

        # Анализ инвестиций
        text += "\n📊 АНАЛИЗ ИНВЕСТИЦИЙ\n"
        text += "-" * 50 + "\n"

        allocation = solution.get('allocation', {})
        if allocation:
            # Группировка по инструментам
            by_instrument = {}
            for key, alloc in allocation.items():
                instr = alloc.get('instrument', '')
                amount = alloc.get('amount', 0)
                if instr not in by_instrument:
                    by_instrument[instr] = 0
                by_instrument[instr] += amount

            for instr, amount in sorted(by_instrument.items()):
                text += f"• {instr}: {self.format_millions(amount)} млн руб\n"

            # Инвестиции в месяц 1
            month1_investments = [
                alloc for key, alloc in allocation.items()
                if alloc.get('start_month') == 1
            ]
            if month1_investments:
                month1_total = sum(a.get('amount', 0) for a in month1_investments)
                text += f"\n• Инвестиции в месяце 1: {self.format_millions(month1_total)} млн руб\n"

                # Проверка необходимости инвестиций вида А в месяце 1
                a_month1 = [a for a in month1_investments if a.get('instrument') == 'A']
                if a_month1:
                    text += f"• Инвестиции вида А в месяце 1: необходимы (сумма: {self.format_millions(a_month1[0]['amount'])} млн руб)\n"
                else:
                    text += f"• Инвестиции вида А в месяце 1: не требуются\n"
        else:
            text += "• Нет активных инвестиций\n"

        # Ответы на вопросы задания
        text += "\n❓ ОТВЕТЫ НА ВОПРОСЫ ЗАДАНИЯ\n"
        text += "-" * 50 + "\n"

        if solution.get('success'):
            if mode == 'basic':
                text += f"1. Размер целевого фонда без ограничений: {self.format_millions(fund_value)} млн руб\n"
            elif mode == 'risk':
                text += f"2. Размер фонда с учетом риска: {self.format_millions(fund_value)} млн руб\n"
            elif mode == 'full':
                text += f"3. Размер фонда с учетом всех ограничений: {self.format_millions(fund_value)} млн руб\n"

        self.analysis_text.setText(text)

    def clear(self):
        """Очистка результатов"""
        self.fund_label.setText("—")
        self.income_label.setText("—")
        self.count_label.setText("—")
        self.mode_label.setText("—")
        self.allocation_table.setRowCount(0)
        self.analysis_text.clear()
        self.current_solution = None