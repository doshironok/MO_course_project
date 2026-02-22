#!/usr/bin/env python3
"""
Тесты для проверки работы оптимизатора инвестиционного портфеля
"""

import sys
import os
from pprint import pprint

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.optimizer import InvestmentOptimizer
from utils.constants import INVESTMENTS, PAYMENTS, RISK_LIMIT, DURATION_LIMIT


def print_separator(title):
    """Вывод разделителя с заголовком"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_availability():
    """Тест 1: Проверка доступности инструментов по месяцам"""
    print_separator("ТЕСТ 1: Доступность инструментов по месяцам")

    print("\nКогда доступны деньги от инвестиций (месяц получения):")
    print("-" * 50)

    for month in range(1, 8):
        found = False
        print(f"\nМесяц {month}:")
        for inv in INVESTMENTS:
            for start in inv['start_months']:
                available = start + inv['duration'] - 1
                if available == month:
                    print(f"  ✅ {inv['name']}: старт {start}, срок {inv['duration']} мес, ставка {inv['rate']}%")
                    found = True
        if not found:
            print(f"  ❌ Нет инструментов, доступных в месяце {month}")


def test_basic_calculation():
    """Тест 2: Базовый расчет без ограничений"""
    print_separator("ТЕСТ 2: Базовый расчет без ограничений")

    optimizer = InvestmentOptimizer()

    print("\nИсходные данные:")
    print(f"  Платеж через 2 месяца: {PAYMENTS[2]} млн руб")
    print(f"  Платеж через 6 месяцев: {PAYMENTS[6]} млн руб")
    print("\nИнструменты:")
    for inv in INVESTMENTS:
        print(f"  {inv['name']}: срок {inv['duration']} мес, ставка {inv['rate']}%, риск {inv['risk']}")

    # Построение модели
    model = optimizer.build_model(
        investments=INVESTMENTS,
        payments=PAYMENTS,
        risk_limit=RISK_LIMIT,
        duration_limit=DURATION_LIMIT,
        mode='basic'
    )

    # Решение
    solution = optimizer.solve(model)

    if solution['success']:
        print(f"\n✅ РЕШЕНИЕ НАЙДЕНО")
        print(f"  Начальный фонд: {solution['fun']:.2f} млн руб")
        print(f"  Общая доходность: {solution.get('total_income', 0):.2f} млн руб")

        print("\nРаспределение инвестиций:")
        print("-" * 60)
        alloc_df = optimizer.get_allocation_dataframe(solution)
        if not alloc_df.empty:
            print(alloc_df.to_string(index=False))
        else:
            print("  Нет инвестиций")
    else:
        print(f"\n❌ РЕШЕНИЕ НЕ НАЙДЕНО: {solution['message']}")


def test_risk_constraint():
    """Тест 3: Расчет с учетом ограничений по риску"""
    print_separator("ТЕСТ 3: Расчет с учетом ограничений по риску")

    optimizer = InvestmentOptimizer()

    print(f"\nОграничение по риску: ≤ {RISK_LIMIT}")

    model = optimizer.build_model(
        investments=INVESTMENTS,
        payments=PAYMENTS,
        risk_limit=RISK_LIMIT,
        duration_limit=DURATION_LIMIT,
        mode='risk'
    )

    solution = optimizer.solve(model)

    if solution['success']:
        print(f"\n✅ РЕШЕНИЕ НАЙДЕНО")
        print(f"  Начальный фонд: {solution['fun']:.2f} млн руб")

        print("\nРаспределение инвестиций:")
        print("-" * 60)
        alloc_df = optimizer.get_allocation_dataframe(solution)
        if not alloc_df.empty:
            print(alloc_df.to_string(index=False))
        else:
            print("  Нет инвестиций")

        # Проверка соблюдения риска
        print("\nАнализ риска по месяцам:")
        print("-" * 60)
        for month in range(1, 7):
            risk = solution['monthly_risk'][month - 1]
            status = "✅" if risk <= RISK_LIMIT else "❌"
            print(f"  Месяц {month}: риск = {risk:.2f} {status}")
    else:
        print(f"\n❌ РЕШЕНИЕ НЕ НАЙДЕНО: {solution['message']}")


def test_full_constraints():
    """Тест 4: Полный расчет (риск + срок)"""
    print_separator("ТЕСТ 4: Полный расчет (риск + срок)")

    optimizer = InvestmentOptimizer()

    print(f"\nОграничения:")
    print(f"  Риск: ≤ {RISK_LIMIT}")
    print(f"  Срок погашения: ≤ {DURATION_LIMIT} месяцев")

    model = optimizer.build_model(
        investments=INVESTMENTS,
        payments=PAYMENTS,
        risk_limit=RISK_LIMIT,
        duration_limit=DURATION_LIMIT,
        mode='full'
    )

    solution = optimizer.solve(model)

    if solution['success']:
        print(f"\n✅ РЕШЕНИЕ НАЙДЕНО")
        print(f"  Начальный фонд: {solution['fun']:.2f} млн руб")

        print("\nРаспределение инвестиций:")
        print("-" * 60)
        alloc_df = optimizer.get_allocation_dataframe(solution)
        if not alloc_df.empty:
            print(alloc_df.to_string(index=False))
        else:
            print("  Нет инвестиций")

        # Детальный анализ
        print("\nДетальный анализ по месяцам:")
        print("-" * 70)
        print(
            f"{'Месяц':^6} | {'Активы':^10} | {'Риск':^10} | {'Риск статус':^12} | {'Срок':^10} | {'Срок статус':^12}")
        print("-" * 70)

        for month in range(1, 7):
            risk = solution['monthly_risk'][month - 1]
            duration = solution['monthly_duration'][month - 1]
            amount = solution['monthly_amount'][month - 1]

            risk_status = "✅" if risk <= RISK_LIMIT else "❌"
            dur_status = "✅" if duration <= DURATION_LIMIT else "❌"

            print(
                f"{month:^6} | {amount:>10.2f} | {risk:>10.2f} | {risk_status:^12} | {duration:>10.2f} | {dur_status:^12}")
    else:
        print(f"\n❌ РЕШЕНИЕ НЕ НАЙДЕНО: {solution['message']}")


def test_compare_scenarios():
    """Тест 5: Сравнение всех трех сценариев"""
    print_separator("ТЕСТ 5: Сравнение всех сценариев")

    optimizer = InvestmentOptimizer()
    results = {}

    modes = [
        ('basic', 'Без ограничений'),
        ('risk', 'Только риск'),
        ('full', 'Риск + срок')
    ]

    for mode, mode_name in modes:
        print(f"\n▶ Режим: {mode_name}")

        model = optimizer.build_model(
            investments=INVESTMENTS,
            payments=PAYMENTS,
            risk_limit=RISK_LIMIT,
            duration_limit=DURATION_LIMIT,
            mode=mode
        )

        solution = optimizer.solve(model)

        if solution['success']:
            results[mode] = solution['fun']
            print(f"  Начальный фонд: {solution['fun']:.2f} млн руб")

            # Какие инструменты используются
            alloc_df = optimizer.get_allocation_dataframe(solution)
            if not alloc_df.empty:
                instruments = sorted(alloc_df['Инструмент'].unique())
                print(f"  Инструменты: {', '.join(instruments)}")
        else:
            results[mode] = None
            print(f"  ❌ Решение не найдено")

    # Сравнение
    print("\n" + "=" * 50)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
    print("=" * 50)

    base_fund = results.get('basic')
    if base_fund:
        for mode, mode_name in [('risk', 'Только риск'), ('full', 'Риск + срок')]:
            if results.get(mode):
                diff = results[mode] - base_fund
                diff_percent = (diff / base_fund) * 100
                print(f"{mode_name:15}: {results[mode]:10.2f} млн руб  (Δ = {diff:+.2f} млн руб, {diff_percent:+.1f}%)")
            else:
                print(f"{mode_name:15}: нет решения")


def test_manual_scenario(payment_2=200, payment_6=700, risk_limit=6.0, duration_limit=2.5, mode='full'):
    """Тест 6: Ручной ввод параметров"""
    print_separator(f"ТЕСТ 6: Ручной сценарий (mode={mode})")

    optimizer = InvestmentOptimizer()

    print(f"\nПараметры:")
    print(f"  Платеж через 2 месяца: {payment_2} млн руб")
    print(f"  Платеж через 6 месяцев: {payment_6} млн руб")
    print(f"  Лимит риска: {risk_limit}")
    print(f"  Лимит срока: {duration_limit}")

    payments = {2: payment_2, 6: payment_6}

    model = optimizer.build_model(
        investments=INVESTMENTS,
        payments=payments,
        risk_limit=risk_limit,
        duration_limit=duration_limit,
        mode=mode
    )

    solution = optimizer.solve(model)

    if solution['success']:
        print(f"\n✅ РЕШЕНИЕ НАЙДЕНО")
        print(f"  Начальный фонд: {solution['fun']:.2f} млн руб")

        print("\nРаспределение инвестиций:")
        alloc_df = optimizer.get_allocation_dataframe(solution)
        if not alloc_df.empty:
            print(alloc_df.to_string(index=False))

            # Ответы на вопросы
            print("\n📌 ОТВЕТЫ НА ВОПРОСЫ:")
            a_month1 = alloc_df[(alloc_df['Инструмент'] == 'A') & (alloc_df['Месяц начала'] == 1)]
            if not a_month1.empty:
                print(f"  • Инвестиции А в месяце 1: ДА ({a_month1.iloc[0]['Сумма (млн руб)']} млн руб)")
            else:
                print(f"  • Инвестиции А в месяце 1: НЕТ")
    else:
        print(f"\n❌ РЕШЕНИЕ НЕ НАЙДЕНО: {solution['message']}")


def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "★" * 70)
    print(" ЗАПУСК ВСЕХ ТЕСТОВ ОПТИМИЗАТОРА")
    print("★" * 70)

    test_availability()
    test_basic_calculation()
    test_risk_constraint()
    test_full_constraints()
    test_compare_scenarios()

    # Дополнительные тесты с разными параметрами
    test_manual_scenario(payment_2=300, payment_6=600, mode='basic')
    test_manual_scenario(risk_limit=5.0, mode='risk')
    test_manual_scenario(duration_limit=2.0, mode='full')


if __name__ == "__main__":
    run_all_tests()