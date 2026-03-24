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
    """Класс для модульного тестирования InvestmentOptimizer"""

    @pytest.fixture
    def optimizer(self):
        return InvestmentOptimizer()

    @pytest.fixture
    def model_basic(self, optimizer):
        return optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )

    @pytest.fixture
    def model_risk(self, optimizer):
        return optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='risk'
        )

    @pytest.fixture
    def model_full(self, optimizer):
        return optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='full'
        )


    def test_generate_variables(self, optimizer):
        """Проверка количества и структуры сгенерированных переменных"""
        variables = optimizer._generate_variables(INVESTMENTS)

        # Проверка количества (A:6, B:3, C:2, O:1 = 12)
        assert len(variables) == 12

        # Проверка структуры
        required_fields = ['name', 'start_month', 'duration', 'rate', 'risk', 'return_month']
        for var in variables:
            for field in required_fields:
                assert field in var

            # Проверка правильности возврата
            assert var['return_month'] == var['start_month'] + var['duration']
            assert var['return_month'] <= 7  # Не позже месяца 7


    def test_build_model_structure(self, optimizer, model_basic, model_risk, model_full):
        """Проверка структуры моделей для разных режимов"""
        required_keys = ['c', 'A_eq', 'b_eq', 'A_ub', 'b_ub', 'bounds',
                         'variables', 'mode', 'n_invest_vars', 'n_balance_vars']

        for model in [model_basic, model_risk, model_full]:
            for key in required_keys:
                assert key in model

        # Проверка количества ограничений
        assert len(model_basic['A_eq']) == 8  # 8 балансов
        assert model_basic['A_ub'] is None or len(model_basic['A_ub']) == 0

        assert len(model_risk['A_ub']) == 6  # 6 ограничений риска
        assert len(model_full['A_ub']) == 12  # 6 риска + 6 срока

        # Проверка корректировки платежей
        assert model_basic['adjusted_payments'][3] == 200  # платёж в конце м2 -> начало м3
        assert model_basic['adjusted_payments'][7] == 700  # платёж в конце м6 -> начало м7


    def test_solve_basic(self, optimizer, model_basic):
        """Проверка решения в режиме BASIC"""
        solution = optimizer.solve_simplex(model_basic)

        assert solution['success']
        assert solution['fun'] > 800 and solution['fun'] < 830
        assert solution['fun_thousand'] == solution['fun'] * 1000

        # Проверка структуры решения
        assert 'monthly_risk' in solution
        assert 'monthly_duration' in solution
        assert 'allocation' in solution

        # В BASIC используются инструменты C (наиболее выгодные)
        has_c = any('C' in name for name, val in zip(solution['var_names'], solution['x']) if val > 1e-3)
        assert has_c


    def test_solve_risk(self, optimizer, model_risk, model_basic):
        """Проверка решения в режиме RISK"""
        solution = optimizer.solve_simplex(model_risk)
        basic_solution = optimizer.solve_simplex(model_basic)

        assert solution['success']
        assert solution['fun'] >= basic_solution['fun'] - 1e-6  # риск не уменьшает фонд

        # Проверка соблюдения ограничений по риску
        for month in range(1, 7):
            risk_val = solution['monthly_risk'][month - 1]
            if solution['monthly_amount'][month - 1] > 1e-3:
                assert risk_val <= 6.0 + 1e-6

        # В RISK используются A для снижения риска
        has_a = any('A' in name for name, val in zip(solution['var_names'], solution['x']) if val > 1e-3)
        assert has_a


    def test_solve_full(self, optimizer, model_full):
        """Проверка решения в режиме FULL"""
        solution = optimizer.solve_simplex(model_full)

        assert solution['success']

        # Проверка соблюдения ограничений по риску и сроку
        for month in range(1, 7):
            risk_val = solution['monthly_risk'][month - 1]
            dur_val = solution['monthly_duration'][month - 1]
            if solution['monthly_amount'][month - 1] > 1e-3:
                assert risk_val <= 6.0 + 1e-6
                assert dur_val <= 2.5 + 1e-6


    def test_monotonicity(self, optimizer):
        """Проверка: BASIC ≤ RISK ≤ FULL"""
        basic = optimizer.solve_simplex(
            optimizer.build_simplex_model(INVESTMENTS, PAYMENTS, RISK_LIMIT, DURATION_LIMIT, 'basic')
        )
        risk = optimizer.solve_simplex(
            optimizer.build_simplex_model(INVESTMENTS, PAYMENTS, RISK_LIMIT, DURATION_LIMIT, 'risk')
        )
        full = optimizer.solve_simplex(
            optimizer.build_simplex_model(INVESTMENTS, PAYMENTS, RISK_LIMIT, DURATION_LIMIT, 'full')
        )

        assert basic['fun'] <= risk['fun'] + 1e-6
        assert risk['fun'] <= full['fun'] + 1e-6


    def test_zero_payments(self, optimizer):
        """Проверка с нулевыми платежами"""
        zero_payments = {2: 0, 6: 0}
        model = optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=zero_payments,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )

        solution = optimizer.solve_simplex(model)
        assert solution['success']
        assert sum(solution['x']) == pytest.approx(0, abs=1e-3)

    # ========== ТЕСТ 11: Высокий лимит риска ==========
    def test_high_risk_limit(self, optimizer):
        """Проверка с высоким лимитом риска (должно совпадать с BASIC)"""
        high_risk = 100
        model_high = optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=high_risk,
            duration_limit=DURATION_LIMIT,
            mode='risk'
        )
        model_basic = optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )

        solution_high = optimizer.solve_simplex(model_high)
        solution_basic = optimizer.solve_simplex(model_basic)

        assert solution_high['fun'] == pytest.approx(solution_basic['fun'], rel=1e-3)


    def test_nonnegative_investments(self, optimizer, model_risk):
        """Проверка, что все инвестиции неотрицательны"""
        solution = optimizer.solve_simplex(model_risk)

        for val in solution['x']:
            assert val >= -1e-6  # допускаем малые погрешности


    def test_integration_basic(self, optimizer):
        """Полный цикл для BASIC режима"""
        # Построение модели
        model = optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='basic'
        )
        assert model['mode'] == 'basic'

        # Решение
        solution = optimizer.solve_simplex(model)
        assert solution['success']
        assert solution['fun'] > 0

        # Отчеты
        constraints_df = optimizer.check_constraints(solution)
        allocation_df = optimizer.get_allocation_dataframe(solution)

        assert isinstance(constraints_df, pd.DataFrame)
        assert isinstance(allocation_df, pd.DataFrame)


    def test_integration_full(self, optimizer):
        """Полный цикл для FULL режима"""
        model = optimizer.build_simplex_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode='full'
        )
        assert model['mode'] == 'full'
        assert len(model['A_ub']) == 12

        solution = optimizer.solve_simplex(model)
        assert solution['success']

        constraints_df = optimizer.check_constraints(solution)
        allocation_df = optimizer.get_allocation_dataframe(solution)

        assert isinstance(constraints_df, pd.DataFrame)
        assert isinstance(allocation_df, pd.DataFrame)

        # Проверка соблюдения ограничений
        for month in range(1, 7):
            if solution['monthly_amount'][month - 1] > 1e-3:
                assert solution['monthly_risk'][month - 1] <= 6.0 + 1e-6
                assert solution['monthly_duration'][month - 1] <= 2.5 + 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])