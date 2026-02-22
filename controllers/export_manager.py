"""
Модуль для экспорта отчетов в различные форматы
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox, QApplication
import os

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    import reportlab.rl_config
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ExportManager:
    """
    Класс для экспорта отчетов
    """

    def __init__(self, parent=None):
        self.parent = parent
        self._register_fonts()

    def _register_fonts(self):
        """Регистрация шрифтов с поддержкой кириллицы"""
        if not REPORTLAB_AVAILABLE:
            return

        try:
            # Попытка найти системные шрифты с поддержкой кириллицы
            import platform
            system = platform.system()

            if system == "Windows":
                # Пути к шрифтам в Windows
                font_paths = [
                    "C:\\Windows\\Fonts\\arial.ttf",
                    "C:\\Windows\\Fonts\\times.ttf",
                    "C:\\Windows\\Fonts\\DejaVuSans.ttf"
                ]
            elif system == "Linux":
                # Пути к шрифтам в Linux
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
                ]
            else:  # macOS
                font_paths = [
                    "/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/Helvetica.ttf",
                    "/System/Library/Fonts/Times.ttf"
                ]

            # Регистрация первого найденного шрифта
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                    # Также регистрируем жирную версию
                    bold_path = font_path.replace('.ttf', 'bd.ttf').replace('.ttf', 'Bd.ttf')
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont('CyrillicFont-Bold', bold_path))
                    else:
                        # Если нет жирной версии, используем обычный шрифт
                        pdfmetrics.registerFont(TTFont('CyrillicFont-Bold', font_path))
                    break
            else:
                # Если не нашли ни одного шрифта, используем стандартный Helvetica
                # (кириллица не будет отображаться, но не будет черных квадратов)
                pdfmetrics.registerFont(TTFont('CyrillicFont', 'Helvetica'))
                pdfmetrics.registerFont(TTFont('CyrillicFont-Bold', 'Helvetica-Bold'))

        except Exception as e:
            print(f"Ошибка регистрации шрифтов: {e}")
            # В случае ошибки используем стандартные шрифты
            pass

    def export_to_excel(self, solution: Dict, constraints_df: pd.DataFrame,
                        allocation_df: pd.DataFrame, filename: str) -> bool:
        """
        Экспорт результатов в Excel

        Args:
            solution: результаты оптимизации
            constraints_df: таблица ограничений
            allocation_df: таблица распределения
            filename: имя файла

        Returns:
            True если успешно
        """
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Лист со сводкой
                summary_data = {
                    'Показатель': ['Начальный фонд (млн руб)',
                                  'Общая доходность (млн руб)',
                                  'Количество инвестиций',
                                  'Режим расчета',
                                  'Статус'],
                    'Значение': [
                        round(solution['fun'], 2) if solution['fun'] else 0,
                        round(solution.get('total_income', 0), 2),
                        len(solution.get('allocation', {})),
                        self._get_mode_name(solution['mode']),
                        'Успешно' if solution['success'] else 'Ошибка'
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Сводка', index=False)

                # Лист с распределением
                if not allocation_df.empty:
                    allocation_df.to_excel(writer, sheet_name='Инвестиции', index=False)

                # Лист с анализом ограничений
                if not constraints_df.empty:
                    constraints_df.to_excel(writer, sheet_name='Анализ ограничений', index=False)

            return True

        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка",
                               f"Не удалось экспортировать в Excel: {str(e)}")
            return False

    def export_to_pdf(self, solution: Dict, constraints_df: pd.DataFrame,
                      allocation_df: pd.DataFrame, filename: str) -> bool:
        """
        Экспорт результатов в PDF

        Args:
            solution: результаты оптимизации
            constraints_df: таблица ограничений
            allocation_df: таблица распределения
            filename: имя файла

        Returns:
            True если успешно
        """
        if not REPORTLAB_AVAILABLE:
            QMessageBox.warning(self.parent, "Предупреждение",
                              "Библиотека reportlab не установлена. PDF не будет создан.\n"
                              "Установите: pip install reportlab")
            return False

        try:
            # Создание документа
            doc = SimpleDocTemplate(filename, pagesize=A4,
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)

            # Создание стилей с поддержкой кириллицы
            styles = getSampleStyleSheet()

            # Создание стилей с русским шрифтом
            title_style = ParagraphStyle(
                'RussianTitle',
                parent=styles['Heading1'],
                fontName='CyrillicFont-Bold',
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )

            heading_style = ParagraphStyle(
                'RussianHeading',
                parent=styles['Heading2'],
                fontName='CyrillicFont-Bold',
                fontSize=14,
                spaceBefore=15,
                spaceAfter=10
            )

            normal_style = ParagraphStyle(
                'RussianNormal',
                parent=styles['Normal'],
                fontName='CyrillicFont',
                fontSize=10,
                spaceBefore=6,
                spaceAfter=6
            )

            elements = []

            # Заголовок
            title_text = "Отчет об оптимизации инвестиционного портфеля"
            elements.append(Paragraph(title_text, title_style))

            date_text = f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            elements.append(Paragraph(date_text, normal_style))
            elements.append(Spacer(1, 0.5*cm))

            # Сводка
            elements.append(Paragraph("Основные показатели", heading_style))
            elements.append(Spacer(1, 0.3*cm))

            summary_data = [
                ['Показатель', 'Значение'],
                ['Начальный фонд (млн руб)', f"{round(solution['fun'], 2) if solution['fun'] else 0}"],
                ['Общая доходность (млн руб)', f"{round(solution.get('total_income', 0), 2)}"],
                ['Количество инвестиций', str(len(solution.get('allocation', {})))],
                ['Режим расчета', self._get_mode_name(solution['mode'])],
                ['Статус', 'Успешно' if solution['success'] else 'Ошибка']
            ]

            # Создание таблицы со стилями
            table = Table(summary_data, colWidths=[8*cm, 6*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'CyrillicFont-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'CyrillicFont'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))

            # Распределение инвестиций
            if not allocation_df.empty:
                elements.append(Paragraph("Распределение инвестиций", heading_style))
                elements.append(Spacer(1, 0.3*cm))

                # Преобразование DataFrame в список для таблицы
                headers = [str(h) for h in allocation_df.columns.tolist()]
                alloc_data = [headers]

                for _, row in allocation_df.iterrows():
                    row_data = [str(row[col]) for col in allocation_df.columns]
                    alloc_data.append(row_data)

                # Расчет ширины колонок
                col_widths = [4*cm, 3*cm, 3*cm, 3*cm, 2*cm]

                alloc_table = Table(alloc_data, colWidths=col_widths, repeatRows=1)
                alloc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'CyrillicFont-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'CyrillicFont'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                ]))
                elements.append(alloc_table)
                elements.append(Spacer(1, 0.5*cm))

            # Анализ ограничений
            if not constraints_df.empty:
                elements.append(Paragraph("Анализ соблюдения ограничений", heading_style))
                elements.append(Spacer(1, 0.3*cm))

                # Преобразование DataFrame в список для таблицы
                headers = [str(h) for h in constraints_df.columns.tolist()]
                constraints_data = [headers]

                for _, row in constraints_df.iterrows():
                    row_data = []
                    for col in constraints_df.columns:
                        value = row[col]
                        if isinstance(value, float):
                            row_data.append(f"{value:.2f}")
                        else:
                            row_data.append(str(value))
                    constraints_data.append(row_data)

                # Расчет ширины колонок
                col_widths = [2*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm]

                constraints_table = Table(constraints_data, colWidths=col_widths, repeatRows=1)

                # Функция для определения цвета строк в зависимости от статуса
                style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'CyrillicFont-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'CyrillicFont'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]

                # Добавляем цвета для строк с нарушениями
                for i, row in enumerate(constraints_data[1:], start=1):
                    if 'Нарушение' in row[3] or 'Нарушение' in row[6]:
                        style.append(('BACKGROUND', (0, i), (-1, i), colors.pink))
                    else:
                        if i % 2 == 0:
                            style.append(('BACKGROUND', (0, i), (-1, i), colors.white))
                        else:
                            style.append(('BACKGROUND', (0, i), (-1, i), colors.lightgrey))

                constraints_table.setStyle(TableStyle(style))
                elements.append(constraints_table)
                elements.append(Spacer(1, 0.5*cm))

                # Добавляем информацию о нарушениях
                violations_risk = constraints_df[constraints_df['Риск статус'] == 'Нарушение']
                violations_dur = constraints_df[constraints_df['Срок статус'] == 'Нарушение']

                if len(violations_risk) > 0 or len(violations_dur) > 0:
                    elements.append(Paragraph("Обнаруженные нарушения:", heading_style))
                    if len(violations_risk) > 0:
                        risk_months = [str(int(m)) for m in violations_risk['Месяц'].values]
                        elements.append(Paragraph(
                            f"• Нарушения по риску в месяцах: {', '.join(risk_months)}",
                            normal_style
                        ))
                    if len(violations_dur) > 0:
                        dur_months = [str(int(m)) for m in violations_dur['Месяц'].values]
                        elements.append(Paragraph(
                            f"• Нарушения по сроку в месяцах: {', '.join(dur_months)}",
                            normal_style
                        ))

            # Добавляем ответы на вопросы задания
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("Ответы на вопросы задания", heading_style))

            answers = self._generate_answers(solution, allocation_df)
            for answer in answers:
                elements.append(Paragraph(f"• {answer}", normal_style))

            # Построение PDF
            doc.build(elements)
            return True

        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка",
                               f"Не удалось экспортировать в PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _get_mode_name(self, mode: str) -> str:
        """Получение названия режима расчета"""
        mode_names = {
            'basic': 'Без ограничений',
            'risk': 'С учетом риска',
            'full': 'Полный (риск + срок)'
        }
        return mode_names.get(mode, mode)

    def _generate_answers(self, solution: Dict, allocation_df: pd.DataFrame) -> list:
        """Генерация ответов на вопросы задания"""
        answers = []

        if not solution['success']:
            answers.append("Решение не найдено")
            return answers

        # 1. Размер целевого фонда без учета ограничений
        if solution['mode'] == 'basic':
            answers.append(f"Размер целевого фонда без ограничений: {round(solution['fun'], 2)} млн руб")

        # 2. Необходимость инвестиций вида А в месяце 1
        if not allocation_df.empty:
            a_month1 = allocation_df[
                (allocation_df['Инструмент'] == 'A') &
                (allocation_df['Месяц начала'] == 1)
            ]
            if len(a_month1) > 0:
                answers.append(f"Инвестиции вида А в месяце 1: необходимы (сумма: {a_month1.iloc[0]['Сумма (млн руб)']} млн руб)")
            else:
                answers.append("Инвестиции вида А в месяце 1: не требуются")

        # 3. Размер фонда с учетом риска
        if solution['mode'] == 'risk':
            answers.append(f"Размер фонда с учетом риска: {round(solution['fun'], 2)} млн руб")

        # 4. Размер фонда с учетом всех ограничений
        if solution['mode'] == 'full':
            answers.append(f"Размер фонда с учетом всех ограничений: {round(solution['fun'], 2)} млн руб")

        return answers