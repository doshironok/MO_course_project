"""
Модуль вкладки отображения результатов
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pandas as pd


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

        # Группа основных показателей
        summary_group = QGroupBox("Основные показатели")
        summary_layout = QGridLayout()

        summary_layout.addWidget(QLabel("Начальный фонд:"), 0, 0)
        self.fund_label = QLabel("—")
        self.fund_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        summary_layout.addWidget(self.fund_label, 0, 1)
        summary_layout.addWidget(QLabel("млн руб"), 0, 2)

        summary_layout.addWidget(QLabel("Общая доходность:"), 1, 0)
        self.income_label = QLabel("—")
        self.income_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        summary_layout.addWidget(self.income_label, 1, 1)
        summary_layout.addWidget(QLabel("млн руб"), 1, 2)

        summary_layout.addWidget(QLabel("Количество инвестиций:"), 2, 0)
        self.count_label = QLabel("—")
        self.count_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        summary_layout.addWidget(self.count_label, 2, 1)

        summary_layout.addWidget(QLabel("Режим расчета:"), 3, 0)
        self.mode_label = QLabel("—")
        self.mode_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        summary_layout.addWidget(self.mode_label, 3, 1)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Группа распределения инвестиций
        allocation_group = QGroupBox("Распределение инвестиций")
        allocation_layout = QVBoxLayout()

        self.allocation_table = QTableWidget()
        self.allocation_table.setColumnCount(5)
        self.allocation_table.setHorizontalHeaderLabels(
            ["Инструмент", "Месяц начала", "Сумма (млн руб)", "Доход (млн руб)", "Риск"]
        )
        self.allocation_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        allocation_layout.addWidget(self.allocation_table)

        allocation_group.setLayout(allocation_layout)
        layout.addWidget(allocation_group)

        # Группа анализа ограничений
        constraints_group = QGroupBox("Анализ ограничений")
        constraints_layout = QVBoxLayout()

        self.constraints_text = QTextEdit()
        self.constraints_text.setReadOnly(True)
        self.constraints_text.setMaximumHeight(150)
        constraints_layout.addWidget(self.constraints_text)

        constraints_group.setLayout(constraints_layout)
        layout.addWidget(constraints_group)

        self.setLayout(layout)

    def display_results(self, solution: dict, constraints_df: pd.DataFrame, allocation_df: pd.DataFrame):
        """
        Отображение результатов

        Args:
            solution: словарь с решением
            constraints_df: таблица ограничений
            allocation_df: таблица распределения
        """
        self.current_solution = solution

        if not solution['success']:
            self.fund_label.setText("Ошибка")
            self.income_label.setText("—")
            self.count_label.setText("—")
            self.mode_label.setText(solution['mode'])
            self.constraints_text.setText(f"Решение не найдено: {solution['message']}")
            self.allocation_table.setRowCount(0)
            return

        # Основные показатели
        self.fund_label.setText(f"{round(solution['fun'], 2)}")
        self.income_label.setText(f"{round(solution.get('total_income', 0), 2)}")
        self.count_label.setText(str(len(solution.get('allocation', {}))))

        mode_names = {'basic': 'Без ограничений', 'risk': 'С учетом риска', 'full': 'Полный'}
        self.mode_label.setText(mode_names.get(solution['mode'], solution['mode']))

        # Таблица распределения
        self.allocation_table.setRowCount(len(allocation_df))
        for i, row in allocation_df.iterrows():
            self.allocation_table.setItem(i, 0, QTableWidgetItem(str(row['Инструмент'])))
            self.allocation_table.setItem(i, 1, QTableWidgetItem(str(row['Месяц начала'])))
            self.allocation_table.setItem(i, 2, QTableWidgetItem(str(row['Сумма (млн руб)'])))
            self.allocation_table.setItem(i, 3, QTableWidgetItem(str(row['Доход (млн руб)'])))
            self.allocation_table.setItem(i, 4, QTableWidgetItem(str(row['Риск'])))

        # Анализ ограничений
        if not constraints_df.empty:
            text = "Результаты проверки ограничений:\n\n"
            for _, row in constraints_df.iterrows():
                text += f"Месяц {int(row['Месяц'])}: "
                text += f"риск = {row['Риск факт']} ({row['Риск статус']}), "
                text += f"срок = {row['Срок факт']} ({row['Срок статус']}), "
                text += f"активы = {row['Сумма активов']} млн руб\n"
            self.constraints_text.setText(text)
        else:
            self.constraints_text.setText("Нет данных для анализа")

    def clear(self):
        """Очистка результатов"""
        self.fund_label.setText("—")
        self.income_label.setText("—")
        self.count_label.setText("—")
        self.mode_label.setText("—")
        self.allocation_table.setRowCount(0)
        self.constraints_text.clear()
        self.current_solution = None