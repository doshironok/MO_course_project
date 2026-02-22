"""
Модуль вкладки анализа
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pandas as pd


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

        # Группа информации о решении
        info_group = QGroupBox("Информация о решении")
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("Статус:"), 0, 0)
        self.status_label = QLabel("—")
        info_layout.addWidget(self.status_label, 0, 1)

        info_layout.addWidget(QLabel("Режим расчета:"), 1, 0)
        self.mode_label = QLabel("—")
        info_layout.addWidget(self.mode_label, 1, 1)

        info_layout.addWidget(QLabel("Сообщение:"), 2, 0)
        self.message_label = QLabel("—")
        info_layout.addWidget(self.message_label, 2, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Группа детального анализа ограничений
        constraints_group = QGroupBox("Детальный анализ ограничений")
        constraints_layout = QVBoxLayout()

        self.constraints_table = QTableWidget()
        self.constraints_table.setColumnCount(8)
        self.constraints_table.setHorizontalHeaderLabels(
            ["Месяц", "Риск факт", "Риск лимит", "Статус",
             "Срок факт", "Срок лимит", "Статус", "Активы"]
        )
        self.constraints_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        constraints_layout.addWidget(self.constraints_table)

        constraints_group.setLayout(constraints_layout)
        layout.addWidget(constraints_group)

        # Группа выводов и рекомендаций
        conclusions_group = QGroupBox("Выводы и рекомендации")
        conclusions_layout = QVBoxLayout()

        self.conclusions_text = QTextEdit()
        self.conclusions_text.setReadOnly(True)
        self.conclusions_text.setMaximumHeight(150)
        conclusions_layout.addWidget(self.conclusions_text)

        conclusions_group.setLayout(conclusions_layout)
        layout.addWidget(conclusions_group)

        self.setLayout(layout)

    def set_data(self, solution: dict, constraints_df: pd.DataFrame, allocation_df: pd.DataFrame):
        """
        Установка данных для анализа

        Args:
            solution: словарь с решением
            constraints_df: таблица ограничений
            allocation_df: таблица распределения
        """
        self.current_solution = solution
        self.constraints_df = constraints_df
        self.allocation_df = allocation_df

        self.update_display()

    def update_display(self):
        """Обновление отображения"""
        if not self.current_solution:
            return

        # Информация о решении
        mode_names = {'basic': 'Без ограничений', 'risk': 'С учетом риска', 'full': 'Полный'}

        self.status_label.setText("Успешно" if self.current_solution.get('success') else "Ошибка")
        self.mode_label.setText(mode_names.get(self.current_solution.get('mode', ''), '—'))
        self.message_label.setText(self.current_solution.get('message', '—'))

        # Таблица ограничений
        if self.constraints_df is not None and not self.constraints_df.empty:
            self.constraints_table.setRowCount(len(self.constraints_df))

            for i, row in self.constraints_df.iterrows():
                self.constraints_table.setItem(i, 0, QTableWidgetItem(str(int(row['Месяц']))))
                self.constraints_table.setItem(i, 1, QTableWidgetItem(str(row['Риск факт'])))
                self.constraints_table.setItem(i, 2, QTableWidgetItem(str(row['Риск лимит'])))

                status_risk = QTableWidgetItem(str(row['Риск статус']))
                if row['Риск статус'] == 'Нарушение':
                    status_risk.setForeground(QBrush(Qt.GlobalColor.red))
                self.constraints_table.setItem(i, 3, status_risk)

                self.constraints_table.setItem(i, 4, QTableWidgetItem(str(row['Срок факт'])))
                self.constraints_table.setItem(i, 5, QTableWidgetItem(str(row['Срок лимит'])))

                status_dur = QTableWidgetItem(str(row['Срок статус']))
                if row['Срок статус'] == 'Нарушение':
                    status_dur.setForeground(QBrush(Qt.GlobalColor.red))
                self.constraints_table.setItem(i, 6, status_dur)

                self.constraints_table.setItem(i, 7, QTableWidgetItem(str(row['Сумма активов'])))
        else:
            self.constraints_table.setRowCount(1)
            self.constraints_table.setItem(0, 0, QTableWidgetItem("Нет данных"))

        # Выводы и рекомендации
        self._generate_conclusions()

    def _generate_conclusions(self):
        """Формирование выводов и рекомендаций"""
        if not self.current_solution or not self.current_solution.get('success'):
            self.conclusions_text.setText("Нет данных для формирования выводов")
            return

        text = "### Анализ результатов оптимизации ###\n\n"

        # Основной вывод
        text += f"Начальный фонд: {round(self.current_solution['fun'], 2)} млн руб\n"
        text += f"Общая доходность: {round(self.current_solution.get('total_income', 0), 2)} млн руб\n\n"

        # Анализ ограничений
        if self.constraints_df is not None and not self.constraints_df.empty:
            violations_risk = self.constraints_df[self.constraints_df['Риск статус'] == 'Нарушение']
            violations_dur = self.constraints_df[self.constraints_df['Срок статус'] == 'Нарушение']

            text += "Соблюдение ограничений:\n"
            text += f"- Нарушений по риску: {len(violations_risk)}\n"
            text += f"- Нарушений по сроку: {len(violations_dur)}\n\n"

            if len(violations_risk) > 0:
                text += f"Месяцы с нарушением риска: {list(violations_risk['Месяц'].values)}\n"
            if len(violations_dur) > 0:
                text += f"Месяцы с нарушением срока: {list(violations_dur['Месяц'].values)}\n\n"

        # Анализ инвестиций
        if self.allocation_df is not None and not self.allocation_df.empty:
            max_investment = self.allocation_df.loc[self.allocation_df['Сумма (млн руб)'].idxmax()]
            text += f"Максимальная инвестиция: {max_investment['Инструмент']} "
            text += f"(месяц {max_investment['Месяц начала']}, "
            text += f"{max_investment['Сумма (млн руб)']} млн руб)\n"

            by_instrument = self.allocation_df.groupby('Инструмент')['Сумма (млн руб)'].sum()
            text += "Распределение по инструментам:\n"
            for instr, amount in by_instrument.items():
                text += f"  {instr}: {round(amount, 2)} млн руб ({round(amount / self.current_solution['fun'] * 100, 1)}%)\n"

        # Ответы на вопросы задания
        text += "\n=== Ответы на вопросы задания ===\n"
        text += f"1. Размер целевого фонда без ограничений: "
        text += f"{round(self.current_solution['fun'], 2) if self.current_solution['mode'] == 'basic' else '—'} млн руб\n"

        # Проверка необходимости инвестиций А в месяце 1
        if self.allocation_df is not None and not self.allocation_df.empty:
            a_month1 = self.allocation_df[
                (self.allocation_df['Инструмент'] == 'A') &
                (self.allocation_df['Месяц начала'] == 1)
                ]
            text += f"2. Инвестиции вида А в месяце 1: {'необходимы' if len(a_month1) > 0 else 'не требуются'}\n"

        text += f"3. Размер фонда с учетом риска: "
        text += f"{round(self.current_solution['fun'], 2) if self.current_solution['mode'] == 'risk' else '—'} млн руб\n"

        text += f"4. Размер фонда с учетом всех ограничений: "
        text += f"{round(self.current_solution['fun'], 2) if self.current_solution['mode'] == 'full' else '—'} млн руб\n"

        self.conclusions_text.setText(text)