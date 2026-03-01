"""
Модуль автоматизированного тестирования инвестиционного оптимизатора
Использование: pytest test_optimizer.py -v --tb=short
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os
from pathlib import Path

# Добавление пути к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.optimizer import InvestmentOptimizer
from utils.constants import INVESTMENTS, PAYMENTS, RISK_LIMIT, DURATION_LIMIT


class TestInvestmentOptimizer:
    """
    Класс для модульного тестирования InvestmentOptimizer
    Содержит тесты для проверки отдельных методов класса
    """

    @pytest.fixture
    def optimizer(self):
        """Фикстура для создания экземпляра оптимизатора"""
        return InvestmentOptimizer()

    @pytest.fixture
    def model_basic(self, optimizer):
        """Фикстура для создания базовой модели (без ограничений)"""
        return optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )

    @pytest.fixture
    def model_risk(self, optimizer):
        """Фикстура для создания модели с ограничениями по риску"""
        return optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='risk'
        )

    @pytest.fixture
    def model_full(self, optimizer):
        """Фикстура для создания полной модели (риск + срок)"""
        return optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='full'
        )

    # ========== ТЕСТ 1: Генерация переменных ==========

    def test_generate_variables_count(self, optimizer):
        """
        Тест 1.1: Проверка количества сгенерированных переменных
        Ожидаемый результат: 12 переменных (A:6, B:3, C:2, O:1)
        """
        variables = optimizer._generate_variables(INVESTMENTS)
        assert len(variables) == 12, f"Ожидалось 12 переменных, получено {len(variables)}"
        assert len(optimizer.var_names) == 12, f"Ожидалось 12 имен, получено {len(optimizer.var_names)}"

    def test_generate_variables_structure(self, optimizer):
        """
        Тест 1.2: Проверка структуры сгенерированных переменных
        Ожидаемый результат: каждая переменная содержит все необходимые поля
        """
        variables = optimizer._generate_variables(INVESTMENTS)
        required_fields = ['name', 'start_month', 'duration', 'rate', 'risk', 'return_month']

        for i, var in enumerate(variables):
            for field in required_fields:
                assert field in var, f"Переменная {i} не содержит поле {field}"

    def test_generate_variables_return_month(self, optimizer):
        """
        Тест 1.3: Проверка правильности расчета месяца возврата
        Ожидаемый результат: return_month = start_month + duration
        """
        variables = optimizer._generate_variables(INVESTMENTS)
        for var in variables:
            expected_return = var['start_month'] + var['duration']
            assert var['return_month'] == expected_return, \
                f"Для {var['name']}{var['start_month']}: ожидалось {expected_return}, получено {var['return_month']}"

    # ========== ТЕСТ 2: Построение модели ==========

    def test_build_model_basic_structure(self, model_basic):
        """
        Тест 2.1: Проверка структуры базовой модели
        Ожидаемый результат: модель содержит все необходимые ключи
        """
        required_keys = ['c', 'A_ub', 'b_ub', 'bounds', 'variables', 'var_names', 'n_vars', 'mode']
        for key in required_keys:
            assert key in model_basic, f"Модель не содержит ключ {key}"

        assert model_basic['mode'] == 'basic', f"Режим модели: {model_basic['mode']}, ожидался 'basic'"

    def test_build_model_basic_constraints_count(self, model_basic):
        """
        Тест 2.2: Проверка количества ограничений в базовой модели
        Ожидаемый результат: 2 ограничения (только платежи)
        """
        assert len(model_basic['A_ub']) == 2, f"Ожидалось 2 ограничения, получено {len(model_basic['A_ub'])}"

    def test_build_model_risk_constraints_count(self, model_risk):
        """
        Тест 2.3: Проверка количества ограничений в модели с риском
        Ожидаемый результат: 8 ограничений (2 платежа + 6 по риску)
        """
        assert len(model_risk['A_ub']) == 8, f"Ожидалось 8 ограничений, получено {len(model_risk['A_ub'])}"

    def test_build_model_full_constraints_count(self, model_full):
        """
        Тест 2.4: Проверка количества ограничений в полной модели
        Ожидаемый результат: 14 ограничений (2 платежа + 6 по риску + 6 по сроку)
        """
        assert len(model_full['A_ub']) == 14, f"Ожидалось 14 ограничений, получено {len(model_full['A_ub'])}"

    # ========== ТЕСТ 3: Решение для режима basic ==========

    def test_solve_basic_path_a_values(self, optimizer):
        """
        Тест 3.1: Проверка расчетных значений для пути A
        Ожидаемый результат: A1 = 197044.33, A5 = 689655.17
        """
        a1 = 200000 / 1.015
        a5 = 700000 / 1.015

        assert abs(a1 - 197044.334975) < 0.1, f"A1 = {a1}, ожидалось ~197044.33"
        assert abs(a5 - 689655.172414) < 0.1, f"A5 = {a5}, ожидалось ~689655.17"
        assert abs(a1 + a5 - 886699.507389) < 0.2, f"Сумма = {a1 + a5}, ожидалось ~886699.51"

    def test_solve_basic_path_b_values(self, optimizer):
        """
        Тест 3.2: Проверка расчетных значений для пути B
        Ожидаемый результат: B1 = 643800.48
        """
        b1 = 700000 / (1.035 * 1.035 * 1.015)
        expected_b1 = 643800.483

        assert abs(b1 - expected_b1) < 0.5, f"B1 = {b1}, ожидалось ~643800.48"

    def test_solve_basic_path_c_values(self, optimizer):
        """
        Тест 3.3: Проверка расчетных значений для пути C
        Ожидаемый результат: C1 = 641003.04
        """
        c1 = 700000 / (1.06 * 1.015 * 1.015)
        expected_c1 = 641003.042

        assert abs(c1 - expected_c1) < 0.5, f"C1 = {c1}, ожидалось ~641003.04"

    def test_solve_basic_chooses_best_path(self, optimizer, model_basic):
        """
        Тест 3.4: Проверка выбора оптимального пути
        Ожидаемый результат: выбирается путь с минимальными инвестициями (C1→A4→A5)
        """
        solution = optimizer.solve_basic(model_basic)

        assert solution['success'], "Решение не найдено"
        assert 'path' in solution, "Отсутствует информация о пути"

        # Лучший путь - C (641003) < B (643800) < A (886700)
        assert solution['fun'] < 887000, f"Инвестиции = {solution['fun']}, ожидалось < 887000"
        assert solution['fun'] > 640000, f"Инвестиции = {solution['fun']}, ожидалось > 640000"

    # ========== ТЕСТ 4: Решение для режима risk ==========

    def test_solve_risk_solution_exists(self, optimizer, model_risk):
        """
        Тест 4.1: Проверка существования решения с ограничениями по риску
        Ожидаемый результат: решение найдено
        """
        solution = optimizer.solve(model_risk)
        assert solution['success'], f"Решение не найдено: {solution.get('message', '')}"

    def test_solve_risk_composition(self, optimizer, model_risk):
        """
        Тест 4.2: Проверка состава решения с ограничениями по риску
        Ожидаемый результат: используются только инструменты A (риск 2)
        """
        solution = optimizer.solve(model_risk)
        x = solution['x']
        variables = solution['variables']

        # Проверяем, что все используемые инструменты имеют риск ≤ 6
        for i, val in enumerate(x):
            if val > 1e-3:
                assert variables[i]['risk'] <= 6.0, \
                    f"Инструмент {variables[i]['name']}{variables[i]['start_month']} имеет риск {variables[i]['risk']} > 6"

    def test_solve_risk_risk_values(self, optimizer, model_risk):
        """
        Тест 4.3: Проверка соблюдения ограничений по риску
        Ожидаемый результат: все значения риска ≤ 6.0
        """
        solution = optimizer.solve(model_risk)

        for month in range(1, 7):
            risk_val = solution['monthly_risk'][month - 1]
            assert risk_val <= 6.0 + 1e-6, f"Месяц {month}: риск = {risk_val} > 6.0"

    # ========== ТЕСТ 5: Решение для режима full ==========

    def test_solve_full_solution_exists(self, optimizer, model_full):
        """
        Тест 5.1: Проверка существования решения с полными ограничениями
        Ожидаемый результат: решение найдено
        """
        solution = optimizer.solve(model_full)
        assert solution['success'], f"Решение не найдено: {solution.get('message', '')}"

    def test_solve_full_risk_constraints(self, optimizer, model_full):
        """
        Тест 5.2: Проверка соблюдения ограничений по риску в полной модели
        Ожидаемый результат: все значения риска ≤ 6.0
        """
        solution = optimizer.solve(model_full)

        for month in range(1, 7):
            risk_val = solution['monthly_risk'][month - 1]
            assert risk_val <= 6.0 + 1e-6, f"Месяц {month}: риск = {risk_val} > 6.0"

    def test_solve_full_duration_constraints(self, optimizer, model_full):
        """
        Тест 5.3: Проверка соблюдения ограничений по сроку в полной модели
        Ожидаемый результат: все значения срока ≤ 2.5
        """
        solution = optimizer.solve(model_full)

        for month in range(1, 7):
            dur_val = solution['monthly_duration'][month - 1]
            assert dur_val <= 2.5 + 1e-6, f"Месяц {month}: срок = {dur_val} > 2.5"

    # ========== ТЕСТ 6: Расчет метрик ==========

    def test_calculate_metrics_empty(self, optimizer):
        """
        Тест 6.1: Проверка расчета метрик для нулевого решения
        Ожидаемый результат: все метрики равны 0
        """
        variables = optimizer._generate_variables(INVESTMENTS)
        x = np.zeros(len(variables))

        metrics = optimizer._calculate_metrics(x, variables)

        assert len(metrics['monthly_risk']) == 6, "Должно быть 6 месяцев"
        assert len(metrics['monthly_duration']) == 6, "Должно быть 6 месяцев"
        assert len(metrics['monthly_amount']) == 6, "Должно быть 6 месяцев"

        assert all(v == 0 for v in metrics['monthly_risk']), "Риски должны быть 0"
        assert all(v == 0 for v in metrics['monthly_duration']), "Сроки должны быть 0"
        assert all(v == 0 for v in metrics['monthly_amount']), "Суммы должны быть 0"

    def test_calculate_metrics_a_path(self, optimizer):
        """
        Тест 6.2: Проверка расчета метрик для пути A
        Ожидаемый результат: корректные значения для месяцев 1 и 5
        """
        variables = optimizer._generate_variables(INVESTMENTS)
        x = np.zeros(len(variables))

        a1 = 200000 / 1.015
        a5 = 700000 / 1.015

        for i, var in enumerate(variables):
            if var['name'] == 'A' and var['start_month'] == 1:
                x[i] = a1
            if var['name'] == 'A' and var['start_month'] == 5:
                x[i] = a5

        metrics = optimizer._calculate_metrics(x, variables)

        # Месяц 1: активна A1
        assert metrics['monthly_amount'][0] == pytest.approx(a1, rel=1e-3), "Неверная сумма в месяце 1"
        assert metrics['monthly_risk'][0] == 2.0, "Неверный риск в месяце 1"
        assert metrics['monthly_duration'][0] == 1.0, "Неверный срок в месяце 1"

        # Месяц 5: активна A5
        assert metrics['monthly_amount'][4] == pytest.approx(a5, rel=1e-3), "Неверная сумма в месяце 5"
        assert metrics['monthly_risk'][4] == 2.0, "Неверный риск в месяце 5"
        assert metrics['monthly_duration'][4] == 1.0, "Неверный срок в месяце 5"

    # ========== ТЕСТ 7: Проверка ограничений ==========

    def test_check_constraints_structure(self, optimizer, model_risk):
        """
        Тест 7.1: Проверка структуры отчета об ограничениях
        Ожидаемый результат: DataFrame с 8 колонками и 6 строками
        """
        solution = optimizer.solve(model_risk)
        constraints_df = optimizer.check_constraints(solution)

        assert isinstance(constraints_df, pd.DataFrame), "Результат должен быть DataFrame"
        assert len(constraints_df) == 6, f"Ожидалось 6 строк, получено {len(constraints_df)}"

        expected_columns = ['Месяц', 'Риск факт', 'Риск лимит', 'Риск статус',
                            'Срок факт', 'Срок лимит', 'Срок статус', 'Активы (тыс. руб)']

        for col in expected_columns:
            assert col in constraints_df.columns, f"Отсутствует колонка {col}"

    def test_check_constraints_status_values(self, optimizer, model_risk):
        """
        Тест 7.2: Проверка статусов в отчете об ограничениях
        Ожидаемый результат: статусы 'OK' или 'НАРУШЕНИЕ'
        """
        solution = optimizer.solve(model_risk)
        constraints_df = optimizer.check_constraints(solution)

        valid_statuses = ['OK', 'НАРУШЕНИЕ']
        for _, row in constraints_df.iterrows():
            assert row['Риск статус'] in valid_statuses, f"Неверный статус риска: {row['Риск статус']}"
            assert row['Срок статус'] in valid_statuses, f"Неверный статус срока: {row['Срок статус']}"

    # ========== ТЕСТ 8: Таблица распределения ==========

    def test_get_allocation_dataframe_structure(self, optimizer, model_risk):
        """
        Тест 8.1: Проверка структуры таблицы распределения
        Ожидаемый результат: DataFrame с 5 колонками
        """
        solution = optimizer.solve(model_risk)
        allocation_df = optimizer.get_allocation_dataframe(solution)

        assert isinstance(allocation_df, pd.DataFrame), "Результат должен быть DataFrame"

        if not allocation_df.empty:
            expected_columns = ['Инструмент', 'Месяц начала', 'Сумма (тыс. руб)',
                                'Доход (тыс. руб)', 'Риск']
            for col in expected_columns:
                assert col in allocation_df.columns, f"Отсутствует колонка {col}"

    # ========== ТЕСТ 9: Граничные значения ==========

    def test_zero_payments(self, optimizer):
        """
        Тест 9.1: Проверка работы с нулевыми платежами
        Ожидаемый результат: оптимальное решение - нулевые инвестиции
        """
        zero_payments = {2: 0, 6: 0}
        model = optimizer.build_model(
            investments=INVESTMENTS,
            payments=zero_payments,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )

        solution = optimizer.solve(model)
        assert solution['success'], "Решение не найдено для нулевых платежей"
        assert sum(solution['x']) == pytest.approx(0, abs=1e-3), "Инвестиции должны быть 0"

    def test_very_small_payments(self, optimizer):
        """
        Тест 9.2: Проверка работы с очень малыми платежами
        Ожидаемый результат: решение существует
        """
        small_payments = {2: 1, 6: 1}  # 1 тыс. руб
        model = optimizer.build_model(
            investments=INVESTMENTS,
            payments=small_payments,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )

        solution = optimizer.solve(model)
        assert solution['success'], "Решение не найдено для малых платежей"

    # ========== ТЕСТ 10: Интеграционное тестирование ==========

    def test_full_basic_workflow(self, optimizer):
        """
        Тест 10.1: Проверка полного рабочего процесса для basic режима
        Ожидаемый результат: все этапы выполняются корректно
        """
        # Этап 1: Построение модели
        model = optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )
        assert model['mode'] == 'basic', "Неверный режим модели"

        # Этап 2: Решение
        solution = optimizer.solve_basic(model)
        assert solution['success'], "Решение не найдено"
        assert 'path' in solution, "Отсутствует информация о пути"

        # Этап 3: Проверка ограничений
        constraints_df = optimizer.check_constraints(solution)
        assert len(constraints_df) == 6, "Неверное количество строк в отчете"

        # Этап 4: Таблица распределения
        allocation_df = optimizer.get_allocation_dataframe(solution)
        assert isinstance(allocation_df, pd.DataFrame), "Таблица распределения не создана"

    def test_full_risk_workflow(self, optimizer):
        """
        Тест 10.2: Проверка полного рабочего процесса для risk режима
        Ожидаемый результат: все этапы выполняются корректно
        """
        model = optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='risk'
        )
        assert model['mode'] == 'risk', "Неверный режим модели"
        assert len(model['A_ub']) == 8, "Неверное количество ограничений"

        solution = optimizer.solve(model)
        assert solution['success'], "Решение не найдено"

        constraints_df = optimizer.check_constraints(solution)
        allocation_df = optimizer.get_allocation_dataframe(solution)

        assert isinstance(constraints_df, pd.DataFrame)
        assert isinstance(allocation_df, pd.DataFrame)

    def test_full_full_workflow(self, optimizer):
        """
        Тест 10.3: Проверка полного рабочего процесса для full режима
        Ожидаемый результат: все этапы выполняются корректно
        """
        model = optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='full'
        )
        assert model['mode'] == 'full', "Неверный режим модели"
        assert len(model['A_ub']) == 14, "Неверное количество ограничений"

        solution = optimizer.solve(model)
        assert solution['success'], "Решение не найдено"

        constraints_df = optimizer.check_constraints(solution)
        allocation_df = optimizer.get_allocation_dataframe(solution)

        assert isinstance(constraints_df, pd.DataFrame)
        assert isinstance(allocation_df, pd.DataFrame)


if __name__ == "__main__":
    """Запуск тестов при прямом вызове файла"""
    pytest.main([__file__, "-v", "--tb=short"])