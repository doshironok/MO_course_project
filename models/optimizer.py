"""
Модуль оптимизатора инвестиционного портфеля
Использование симплекс-метода (линейное программирование)
"""

import numpy as np
from scipy.optimize import linprog
import pandas as pd
from typing import Dict, List, Tuple
import traceback


class InvestmentOptimizer:
    def __init__(self):
        self.variables = []
        self.var_names = []
        self.investments = None
        self.payments = None
        self.risk_limit = None
        self.duration_limit = None

    def _generate_variables(self, investments: List[Dict]) -> List[Dict]:
        """Генерация всех возможных инвестиций с корректным временем возврата"""
        variables = []
        self.var_names = []

        for inv in investments:
            for month in inv['start_months']:
                # Возврат в начале месяца month + duration
                return_month = month + inv['duration']

                # Инвестиция имеет смысл если возврат не позже месяца 7
                # (платеж в конце месяца 6 требует средств в начале месяца 7)
                if return_month <= 7:
                    var_info = {
                        'name': inv['name'],
                        'start_month': month,
                        'duration': inv['duration'],
                        'rate': inv['rate'] / 100,
                        'risk': inv['risk'],
                        'return_month': return_month,
                    }
                    variables.append(var_info)
                    self.var_names.append(f"{inv['name']}{month}")

        return variables

    def build_simplex_model(self, investments: List[Dict], payments: Dict,
                            risk_limit: float, duration_limit: float, mode: str) -> Dict:
        """
        Построение модели линейного программирования
        """

        print("\n" + "=" * 80)
        print("ПОСТРОЕНИЕ МОДЕЛИ ЛИНЕЙНОГО ПРОГРАММИРОВАНИЯ")
        print(f"Режим: {mode.upper()}")
        print("=" * 80)

        # Преобразуем платежи: платёж в конце месяца t -> потребность в начале t+1
        adjusted_payments = {}
        for month_end, amount in payments.items():
            adjusted_payments[month_end + 1] = amount

        # Генерируем все возможные инвестиции
        variables = self._generate_variables(investments)
        n_invest_vars = len(variables)

        print(f"\nСгенерированные инвестиции:")
        for i, var in enumerate(variables):
            print(f"  {self.var_names[i]}: старт м{var['start_month']} -> возврат м{var['return_month']}, "
                  f"ставка {var['rate'] * 100:.1f}%, риск {var['risk']}")

        # Переменные:
        # 1. Инвестиции x_i (n_invest_vars)
        # 2. Начальный фонд F (1)
        # 3. Остатки b_1..b_8 (8) — b_t = остаток на начало месяца t ДО инвестиций
        n_balance_vars = 8
        total_vars = n_invest_vars + 1 + n_balance_vars

        print(f"\nВсего переменных: {total_vars}")
        print(f"  Инвестиции: {n_invest_vars}")
        print(f"  Начальный фонд F: 1")
        print(f"  Балансовые b_1..b_8: {n_balance_vars}")

        # Целевая функция: минимизация F
        c = np.zeros(total_vars)
        c[n_invest_vars] = 1  # F

        # ============ ОГРАНИЧЕНИЯ ============
        A_eq = []
        b_eq = []
        A_ub = []
        b_ub = []

        # 1. F = b_1 (начальный фонд равен остатку в начале месяца 1)
        row_start = np.zeros(total_vars)
        row_start[n_invest_vars] = 1  # F
        row_start[n_invest_vars + 1] = -1  # -b_1
        A_eq.append(row_start)
        b_eq.append(0)
        print("\nОграничение 1: F = b_1")

        # 2. Балансовые ограничения для месяцев 1..7
        # b_t + возвраты_t = платеж_t + инвестиции_t + b_{t+1}

        print("\nБалансовые ограничения:")
        for t in range(1, 8):
            row = np.zeros(total_vars)

            # b_t (приход)
            row[n_invest_vars + t] = 1

            # Возвраты от инвестиций (приход)
            for i, var in enumerate(variables):
                if var['return_month'] == t:
                    row[i] = (1 + var['rate'])

            # Инвестиции в начале месяца t (расход)
            for i, var in enumerate(variables):
                if var['start_month'] == t:
                    row[i] -= 1

            # b_{t+1} (расход — остаток на следующий месяц)
            if t < 8:
                row[n_invest_vars + t + 1] = -1

            # Платеж
            payment = adjusted_payments.get(t, 0)

            A_eq.append(row)
            b_eq.append(payment)

            if payment > 0:
                print(f"  Мес{t}: b_{t} + возвраты = {payment} + инвестиции_{t} + b_{t + 1}")
            else:
                print(f"  Мес{t}: b_{t} + возвраты = инвестиции_{t} + b_{t + 1}")

        # 3. Ограничения по риску
        if mode in ['risk', 'full']:
            print("\nОГРАНИЧЕНИЯ ПО РИСКУ (средний взвешенный риск ≤ лимит)")

            for month in range(1, 8):
                row = np.zeros(total_vars)
                has_active = False

                for i, var in enumerate(variables):
                    if var['start_month'] <= month < var['return_month']:
                        row[i] = var['risk'] - risk_limit
                        has_active = True

                if has_active:
                    A_ub.append(row)
                    b_ub.append(0)
                    print(f"  Месяц {month}: Σ (risk_i - {risk_limit})·x_i ≤ 0")

        # 4. Ограничения по сроку погашения
        if mode == 'full':
            print("\nОГРАНИЧЕНИЯ ПО СРОКУ (средний оставшийся срок ≤ лимит)")

            for month in range(1, 8):
                row = np.zeros(total_vars)
                has_active = False

                for i, var in enumerate(variables):
                    if var['start_month'] <= month < var['return_month']:
                        remaining = var['return_month'] - month
                        row[i] = remaining - duration_limit
                        has_active = True

                if has_active:
                    A_ub.append(row)
                    b_ub.append(0)
                    print(f"  Месяц {month}: Σ (remaining_i - {duration_limit})·x_i ≤ 0")

        # 5. Все переменные неотрицательны
        bounds = [(0, None) for _ in range(total_vars)]

        print(f"\nВсего ограничений:")
        print(f"  Равенств: {len(A_eq)}")
        print(f"  Неравенств: {len(A_ub)}")

        model = {
            'c': c,
            'A_eq': np.array(A_eq) if A_eq else None,
            'b_eq': np.array(b_eq) if b_eq else None,
            'A_ub': np.array(A_ub) if A_ub else None,
            'b_ub': np.array(b_ub) if b_ub else None,
            'bounds': bounds,
            'variables': variables,
            'var_names': self.var_names,
            'n_invest_vars': n_invest_vars,
            'n_balance_vars': n_balance_vars,
            'mode': mode,
            'risk_limit': risk_limit,
            'duration_limit': duration_limit,
            'adjusted_payments': adjusted_payments
        }

        return model

    def solve_simplex(self, model: Dict) -> Dict:
        """Решение задачи симплекс-методом"""
        try:
            print("\n" + "=" * 80)
            print("РЕШЕНИЕ ЗАДАЧИ СИМПЛЕКС-МЕТОДОМ")
            print("=" * 80)

            kwargs = {
                'c': model['c'],
                'bounds': model['bounds'],
                'method': 'highs'
            }

            if model['A_eq'] is not None:
                kwargs['A_eq'] = model['A_eq']
                kwargs['b_eq'] = model['b_eq']

            if model['A_ub'] is not None:
                kwargs['A_ub'] = model['A_ub']
                kwargs['b_ub'] = model['b_ub']

            result = linprog(**kwargs)

            print(f"\nСтатус решения: {result.message}")
            print(f"Успешно: {result.success}")

            if result.success:
                print(f"\nОптимальный начальный фонд: {result.fun:.2f} млн руб = {result.fun * 1000:.0f} тыс. руб")

                # Извлекаем переменные
                x_invest = result.x[:model['n_invest_vars']]
                initial_fund = result.x[model['n_invest_vars']]
                balances = result.x[model['n_invest_vars'] + 1:]

                print(f"\nСумма всех инвестиций: {sum(x_invest):.2f} млн руб")
                print(f"Начальный фонд F: {initial_fund:.2f} млн руб")

                print("\nБалансовые переменные (остатки на начало месяца):")
                for t in range(1, 9):
                    b_val = balances[t - 1] if t - 1 < len(balances) else 0
                    if b_val > 1e-3 or t in [1, 2, 3, 7, 8]:
                        print(f"  b_{t}: {b_val:.2f} млн руб")

                print("\nАктивные инвестиции:")
                active_count = 0
                total_invested = 0
                for i, val in enumerate(x_invest):
                    if val > 1e-3:
                        active_count += 1
                        total_invested += val
                        var = model['variables'][i]
                        print(f"  {model['var_names'][i]}: {val:.2f} млн руб "
                              f"(старт м{var['start_month']} -> возврат м{var['return_month']}, "
                              f"ставка {var['rate'] * 100:.1f}%, риск {var['risk']})")

                if active_count == 0:
                    print("  (нет активных инвестиций)")

                # Проверка выполнения ограничений
                print("\nПроверка ограничений:")
                risk_limit = model['risk_limit']
                duration_limit = model['duration_limit']

                metrics = self._calculate_metrics(x_invest, model['variables'])

                for month in range(1, 8):
                    risk_val = metrics['monthly_risk'][month - 1]
                    dur_val = metrics['monthly_duration'][month - 1]
                    amount = metrics['monthly_amount'][month - 1]

                    if amount > 1e-3:
                        risk_ok = "✓" if risk_val <= risk_limit + 1e-6 else "✗"
                        dur_ok = "✓" if dur_val <= duration_limit + 1e-6 else "✗"

                        print(f"  Мес{month}: риск={risk_val:.2f} ({risk_ok}), "
                              f"срок={dur_val:.2f} ({dur_ok}), активы={amount:.2f} млн руб")

                solution = {
                    'success': True,
                    'message': result.message,
                    'fun': result.fun,
                    'fun_thousand': result.fun * 1000,
                    'x': x_invest,
                    'initial_fund': initial_fund,
                    'balances': balances,
                    'variables': model['variables'],
                    'var_names': model['var_names'],
                    'mode': model['mode'],
                    'risk_limit': model['risk_limit'],
                    'duration_limit': model['duration_limit'],
                    **metrics
                }

                analysis_text = self._generate_analysis_text(solution)
                solution['analysis_text'] = analysis_text

                return solution
            else:
                return {
                    'success': False,
                    'message': result.message,
                    'fun': None,
                    'x': None,
                    'variables': model['variables'],
                    'var_names': model['var_names'],
                    'mode': model['mode']
                }

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'message': f"Ошибка: {str(e)}",
                'fun': None,
                'x': None,
                'variables': model['variables'],
                'var_names': model['var_names'],
                'mode': model['mode']
            }

    def _calculate_metrics(self, x: np.ndarray, variables: List[Dict]) -> Dict:
        """Расчет метрик по месяцам (1-7)"""
        monthly_risk = []
        monthly_duration = []
        monthly_amount = []

        # Проверяем месяцы 1-7
        for month in range(1, 8):
            active_amounts = []
            active_risks = []
            active_durations = []

            for i, var in enumerate(variables):
                if var['start_month'] <= month < var['return_month'] and x[i] > 1e-3:
                    active_amounts.append(x[i])
                    active_risks.append(var['risk'])
                    remaining = var['return_month'] - month
                    active_durations.append(remaining)

            total = sum(active_amounts)
            monthly_amount.append(total)

            if total > 1e-3:
                weighted_risk = sum(a * r for a, r in zip(active_amounts, active_risks)) / total
                monthly_risk.append(weighted_risk)
                weighted_duration = sum(a * d for a, d in zip(active_amounts, active_durations)) / total
                monthly_duration.append(weighted_duration)
            else:
                monthly_risk.append(0)
                monthly_duration.append(0)

        # Расчет распределения по инструментам
        allocation = {}
        total_income = 0

        for i, var in enumerate(variables):
            if x[i] > 1e-3:
                income = x[i] * var['rate']
                total_income += income
                key = f"{var['name']}{var['start_month']}"
                allocation[key] = {
                    'instrument': var['name'],
                    'start_month': var['start_month'],
                    'amount': x[i],
                    'income': income,
                    'risk': var['risk'],
                    'duration': var['duration']
                }

        return {
            'monthly_risk': monthly_risk,
            'monthly_duration': monthly_duration,
            'monthly_amount': monthly_amount,
            'allocation': allocation,
            'total_income': total_income
        }

    def _generate_analysis_text(self, solution: Dict) -> str:
        """Генерация текста анализа"""
        x = solution.get('x', [])
        if x is None:
            x = []

        total_sum = sum(x)
        month1_sum = sum(x[i] for i, var in enumerate(solution.get('variables', []))
                        if var['start_month'] == 1 and i < len(x) and x[i] > 1e-3)

        text = f"💰 Начальный фонд: {solution.get('fun', 0):.2f} млн руб\n"
        text += f"   Всего инвестиций: {total_sum:.2f} млн руб\n"
        text += f"   Из них в месяц 1: {month1_sum:.2f} млн руб\n\n"
        text += "📊 Результаты проверки ограничений:\n\n"

        risk_limit = solution.get('risk_limit', 6)
        duration_limit = solution.get('duration_limit', 2.5)

        for month in range(1, 7):
            risk_val = solution.get('monthly_risk', [0]*6)[month-1]
            dur_val = solution.get('monthly_duration', [0]*6)[month-1]
            amount = solution.get('monthly_amount', [0]*6)[month-1]

            risk_status = "✅" if risk_val <= risk_limit + 1e-6 else "❌"
            dur_status = "✅" if dur_val <= duration_limit + 1e-6 else "❌"

            text += f"Месяц {month}: {risk_status} риск = {risk_val:.2f} (лимит {risk_limit:.1f}), "
            text += f"{dur_status} срок = {dur_val:.2f} (лимит {duration_limit:.1f}), "
            text += f"активы = {amount:.2f} млн руб\n"

        return text

    def get_allocation_dataframe(self, solution: Dict) -> pd.DataFrame:
        """Таблица распределения"""
        try:
            if not solution or not solution.get('success'):
                return pd.DataFrame()

            data = []
            allocation = solution.get('allocation', {})
            for key, alloc in allocation.items():
                data.append({
                    'Инструмент': alloc['instrument'],
                    'Месяц начала': alloc['start_month'],
                    'Сумма (млн руб)': round(alloc['amount'], 2),
                    'Доход (млн руб)': round(alloc['income'], 2),
                    'Риск': alloc['risk']
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values(['Инструмент', 'Месяц начала'])

            return df
        except Exception as e:
            print(f"Ошибка в get_allocation_dataframe: {e}")
            return pd.DataFrame()

    def check_constraints(self, solution: Dict) -> pd.DataFrame:
        """Проверка ограничений для отображения"""
        try:
            if not solution or not solution.get('success'):
                return pd.DataFrame()

            months = list(range(1, 7))
            data = []

            monthly_risk = solution.get('monthly_risk', [0] * 6)
            monthly_duration = solution.get('monthly_duration', [0] * 6)
            monthly_amount = solution.get('monthly_amount', [0] * 6)

            risk_limit = solution.get('risk_limit', 6)
            duration_limit = solution.get('duration_limit', 2.5)

            for i, month in enumerate(months):
                risk_value = monthly_risk[i] if i < len(monthly_risk) else 0
                duration_value = monthly_duration[i] if i < len(monthly_duration) else 0
                amount = monthly_amount[i] if i < len(monthly_amount) else 0

                risk_status = 'OK' if risk_value <= risk_limit + 1e-6 else 'НАРУШЕНИЕ'
                duration_status = 'OK' if duration_value <= duration_limit + 1e-6 else 'НАРУШЕНИЕ'

                data.append({
                    'Месяц': month,
                    'Риск факт': round(risk_value, 2),
                    'Риск лимит': risk_limit,
                    'Риск статус': risk_status,
                    'Срок факт': round(duration_value, 2),
                    'Срок лимит': duration_limit,
                    'Срок статус': duration_status,
                    'Активы (млн руб)': round(amount, 2)
                })

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка в check_constraints: {e}")
            return pd.DataFrame()