"""
Модуль вкладки анализа
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pandas as pd
import traceback


class AnalysisTab(QWidget):
    """
    Вкладка для детального анализа результатов
    """

    def __init__(self):
        super().__init__()
        self.current_solution = None
        self.constraints_df = None
        self.allocation_df = None
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel("Детальный анализ")
        title_label.setProperty("role", "heading")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Группа информации о решении
        info_group = QGroupBox("ℹ️ Информация о решении")
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("Статус:"), 0, 0)
        self.status_label = QLabel("—")
        info_layout.addWidget(self.status_label, 0, 1)

        info_layout.addWidget(QLabel("Режим расчета:"), 1, 0)
        self.mode_label = QLabel("—")
        info_layout.addWidget(self.mode_label, 1, 1)

        info_layout.addWidget(QLabel("Сообщение:"), 2, 0)
        self.message_label = QLabel("—")
        self.message_label.setWordWrap(True)
        info_layout.addWidget(self.message_label, 2, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Группа анализа ограничений
        constraints_group = QGroupBox("📋 Анализ ограничений")
        constraints_layout = QVBoxLayout()

        self.constraints_table = QTableWidget()
        self.constraints_table.setColumnCount(8)
        self.constraints_table.setHorizontalHeaderLabels(
            ["Месяц", "Риск факт", "Риск лимит", "Статус",
             "Срок факт", "Срок лимит", "Статус", "Активы (млн руб)"]
        )
        self.constraints_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        constraints_layout.addWidget(self.constraints_table)

        constraints_group.setLayout(constraints_layout)
        layout.addWidget(constraints_group)

        # Группа выводов
        conclusions_group = QGroupBox("💡 Выводы")
        conclusions_layout = QVBoxLayout()

        self.conclusions_text = QTextEdit()
        self.conclusions_text.setReadOnly(True)
        self.conclusions_text.setMaximumHeight(150)
        conclusions_layout.addWidget(self.conclusions_text)

        conclusions_group.setLayout(conclusions_layout)
        layout.addWidget(conclusions_group)

        self.setLayout(layout)

    def set_data(self, solution: dict, constraints_df: pd.DataFrame, allocation_df: pd.DataFrame):
        """Установка данных для анализа"""
        try:
            print("\n=== ANALYSIS TAB SET DATA ===")
            self.current_solution = solution
            self.constraints_df = constraints_df
            self.allocation_df = allocation_df
            self.update_display()
            print("=== ANALYSIS TAB SET DATA FINISHED ===\n")
        except Exception as e:
            print(f"❌ ОШИБКА В SET_DATA: {e}")
            traceback.print_exc()

    def update_display(self):
        """Обновление отображения"""
        try:
            if not self.current_solution:
                print("Нет решения для отображения")
                return

            print("Обновление дисплея анализа...")

            # Статус
            success = self.current_solution.get('success', False)
            self.status_label.setText("✅ Успешно" if success else "❌ Ошибка")

            # Режим
            mode_names = {'basic': 'Без ограничений', 'risk': 'С риском', 'full': 'Полный'}
            mode = self.current_solution.get('mode', '')
            self.mode_label.setText(mode_names.get(mode, mode))

            # Сообщение
            self.message_label.setText(self.current_solution.get('message', '—'))

            # Таблица ограничений
            if self.constraints_df is not None and not self.constraints_df.empty:
                self.constraints_table.setRowCount(len(self.constraints_df))
                for i in range(len(self.constraints_df)):
                    row = self.constraints_df.iloc[i]

                    # Месяц
                    self.constraints_table.setItem(i, 0, QTableWidgetItem(str(int(row.get('Месяц', 0)))))

                    # Риск факт
                    self.constraints_table.setItem(i, 1, QTableWidgetItem(f"{row.get('Риск факт', 0):.2f}"))

                    # Риск лимит
                    self.constraints_table.setItem(i, 2, QTableWidgetItem(f"{row.get('Риск лимит', 6):.1f}"))

                    # Риск статус
                    status_item = QTableWidgetItem(str(row.get('Риск статус', '')))
                    if row.get('Риск статус') == 'НАРУШЕНИЕ':
                        status_item.setForeground(QBrush(Qt.GlobalColor.red))
                    self.constraints_table.setItem(i, 3, status_item)

                    # Срок факт
                    self.constraints_table.setItem(i, 4, QTableWidgetItem(f"{row.get('Срок факт', 0):.2f}"))

                    # Срок лимит
                    self.constraints_table.setItem(i, 5, QTableWidgetItem(f"{row.get('Срок лимит', 2.5):.1f}"))

                    # Срок статус
                    status_item = QTableWidgetItem(str(row.get('Срок статус', '')))
                    if row.get('Срок статус') == 'НАРУШЕНИЕ':
                        status_item.setForeground(QBrush(Qt.GlobalColor.red))
                    self.constraints_table.setItem(i, 6, status_item)

                    # Активы
                    self.constraints_table.setItem(i, 7, QTableWidgetItem(f"{row.get('Активы (млн руб)', 0):.2f}"))
            else:
                self.constraints_table.setRowCount(1)
                self.constraints_table.setItem(0, 0, QTableWidgetItem("Нет данных"))

            # Выводы
            self._generate_conclusions()

        except Exception as e:
            print(f"❌ ОШИБКА В UPDATE_DISPLAY: {e}")
            traceback.print_exc()

    def _generate_conclusions(self):
        """Формирование выводов"""
        try:
            if not self.current_solution or not self.current_solution.get('success'):
                self.conclusions_text.setText("❌ Нет данных для формирования выводов")
                return

            text = "📊 АНАЛИЗ РЕЗУЛЬТАТОВ\n"
            text += "=" * 50 + "\n\n"

            # Начальный фонд
            initial_fund = self.current_solution.get('fun', 0)
            if initial_fund is None:
                initial_fund = 0

            # Считаем только инвестиции в месяце 1
            x = self.current_solution.get('x', [])
            variables = self.current_solution.get('variables', [])

            initial_sum = 0
            if x is not None and len(x) > 0:
                for i, val in enumerate(x):
                    if i < len(variables) and val > 1e-3 and variables[i]['start_month'] == 1:
                        initial_sum += val

            text += f"💰 Начальные инвестиции: {initial_sum/1000:.2f} млн руб\n"

            # Доходность
            total_income = self.current_solution.get('total_income', 0)
            if total_income is None:
                total_income = 0
            text += f"📈 Общая доходность: {total_income/1000:.2f} млн руб\n\n"

            # Анализ инвестиций
            allocation = self.current_solution.get('allocation', {})
            if allocation:
                text += "📊 Распределение:\n"
                for key, alloc in allocation.items():
                    text += f"  • {key}: {alloc['amount']/1000:.2f} млн руб (доход {alloc['income']/1000:.2f} млн руб)\n"

            self.conclusions_text.setText(text)

        except Exception as e:
            print(f"❌ ОШИБКА В GENERATE_CONCLUSIONS: {e}")
            traceback.print_exc()
            self.conclusions_text.setText(f"Ошибка: {str(e)}")