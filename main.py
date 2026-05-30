# Модель: Автоматизоване складання розкладу занять — Генетичний алгоритм (5 семестр)
# Автор: Баранова Анастасія, група АІ-231

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import random
import copy
import os
from typing import List, Dict, Tuple

print(" Імпорт бібліотек завершено!")

# Зчитуємо MODE (непарний варіант → comfort)
MODE = os.environ.get("MODE", "comfort")

if MODE == "comfort":
    DEFAULT_POP_SIZE = 100
    DEFAULT_MAX_ITER = 1000
    DEFAULT_MUTATION = 0.1
elif MODE == "eco":
    DEFAULT_POP_SIZE = 50
    DEFAULT_MAX_ITER = 300
    DEFAULT_MUTATION = 0.2
else:
    DEFAULT_POP_SIZE = 100
    DEFAULT_MAX_ITER = 1000
    DEFAULT_MUTATION = 0.1

print(f"🔧 Режим роботи: MODE={MODE}")
print(f"   Популяція:   {DEFAULT_POP_SIZE}")
print(f"   Ітерації:    {DEFAULT_MAX_ITER}")
print(f"   Мутація:     {DEFAULT_MUTATION}")


class InputData:
    """Зберігає всі вхідні параметри задачі"""

    def __init__(self):
        self.teachers_count = 15
        self.courses_count  = 30
        self.rooms_count    = 12
        self.groups_count   = 10
        self.days_count     = 5
        self.pairs_per_day  = 6
        self.slots_total    = self.days_count * self.pairs_per_day

        self.teachers = self._init_teachers()
        self.courses  = self._init_courses()
        self.rooms    = self._init_rooms()
        self.groups   = self._init_groups()

    def _init_teachers(self):
        result = []
        for i in range(self.teachers_count):
            result.append({
                'id':        i,
                'name':      f'Викладач_{i+1}',
                'preferred': random.sample(range(self.slots_total), random.randint(5, 15))
            })
        return result

    def _init_courses(self):
        result = []
        kinds = ['Лекція', 'Практика', 'Лабораторна']
        for i in range(self.courses_count):
            result.append({
                'id':         i,
                'name':       f'Дисципліна_{i+1}',
                'kind':       random.choice(kinds),
                'teacher_id': random.randint(0, self.teachers_count - 1),
                'group_id':   random.randint(0, self.groups_count - 1),
                'hours':      random.choice([2, 4])
            })
        return result

    def _init_rooms(self):
        result = []
        kinds = ["Лекційна", "Комп'ютерна", 'Лабораторія']
        for i in range(self.rooms_count):
            result.append({
                'id':    i,
                'name':  f'Ауд_{100+i}',
                'seats': random.randint(20, 50),
                'kind':  random.choice(kinds)
            })
        return result

    def _init_groups(self):
        result = []
        for i in range(self.groups_count):
            result.append({
                'id':   i,
                'name': f'Група_{i+1}',
                'size': random.randint(15, 30)
            })
        return result


class GeneticScheduler:
    """Оптимізація розкладу генетичним алгоритмом з локальним пошуком"""

    def __init__(self, data: InputData):
        self.data = data

        self.w_conflicts   = 1000
        self.w_gaps        = 10
        self.w_preferences = 1

        self.pop_size        = int(os.environ.get('POPULATION_SIZE', DEFAULT_POP_SIZE))
        self.max_generations = int(os.environ.get('MAX_ITERATIONS',  DEFAULT_MAX_ITER))
        self.mutation_prob   = float(os.environ.get('MUTATION_RATE', DEFAULT_MUTATION))
        self.tournament_k    = 3

        self.log: List[Dict] = []

    def _random_individual(self) -> List[Dict]:
        individual = []
        for course in self.data.courses:
            individual.append({
                'course_id':    course['id'],
                'course_name':  course['name'],
                'teacher_id':   course['teacher_id'],
                'teacher_name': self.data.teachers[course['teacher_id']]['name'],
                'group_id':     course['group_id'],
                'group_name':   self.data.groups[course['group_id']]['name'],
                'room_id':      random.randint(0, self.data.rooms_count - 1),
                'slot':         random.randint(0, self.data.slots_total - 1),
                'kind':         course['kind']
            })
        return individual

    def _count_conflicts(self, individual: List[Dict]) -> int:
        total = 0
        for slot in range(self.data.slots_total):
            teachers = [e['teacher_id'] for e in individual if e['slot'] == slot]
            total += max(0, len(teachers) - len(set(teachers)))
            rooms = [e['room_id'] for e in individual if e['slot'] == slot]
            total += max(0, len(rooms) - len(set(rooms)))
            groups = [e['group_id'] for e in individual if e['slot'] == slot]
            total += max(0, len(groups) - len(set(groups)))
        for tid in range(self.data.teachers_count):
            for day in range(self.data.days_count):
                s = day * self.data.pairs_per_day
                e = s + self.data.pairs_per_day
                day_classes = [x for x in individual
                               if x['teacher_id'] == tid and s <= x['slot'] < e]
                if len(day_classes) > 4:
                    total += len(day_classes) - 4
        return total

    def _count_gaps(self, individual: List[Dict]) -> int:
        gaps = 0
        for tid in range(self.data.teachers_count):
            for day in range(self.data.days_count):
                s = day * self.data.pairs_per_day
                e = s + self.data.pairs_per_day
                slots = sorted([x['slot'] for x in individual
                                if x['teacher_id'] == tid and s <= x['slot'] < e])
                if len(slots) > 1:
                    for i in range(len(slots) - 1):
                        gaps += max(0, slots[i+1] - slots[i] - 1)
        return gaps

    def _count_pref_deviation(self, individual: List[Dict]) -> int:
        deviation = 0
        for entry in individual:
            preferred = self.data.teachers[entry['teacher_id']]['preferred']
            if entry['slot'] not in preferred:
                deviation += min(abs(entry['slot'] - p) for p in preferred)
        return deviation

    def _fitness(self, individual: List[Dict]) -> float:
        return (self.w_conflicts   * self._count_conflicts(individual) +
                self.w_gaps        * self._count_gaps(individual) +
                self.w_preferences * self._count_pref_deviation(individual))

    def _select(self, population: List, scores: List) -> List:
        selected = []
        for _ in range(len(population) // 2):
            candidates = random.sample(list(zip(population, scores)), self.tournament_k)
            winner = min(candidates, key=lambda x: x[1])
            selected.append(copy.deepcopy(winner[0]))
        return selected

    def _crossover(self, p1: List[Dict], p2: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        pt = random.randint(1, len(p1) - 1)
        return p1[:pt] + p2[pt:], p2[:pt] + p1[pt:]

    def _mutate(self, individual: List[Dict]) -> List[Dict]:
        if random.random() < self.mutation_prob:
            i, j = random.sample(range(len(individual)), 2)
            individual[i]['slot'], individual[j]['slot'] = \
                individual[j]['slot'], individual[i]['slot']
        return individual

    def _local_search(self, individual: List[Dict]) -> List[Dict]:
        improved = True
        iters = 0
        while improved and iters < 50:
            improved = False
            best = self._fitness(individual)
            for i in range(len(individual)):
                for j in range(i + 1, len(individual)):
                    individual[i]['slot'], individual[j]['slot'] = \
                        individual[j]['slot'], individual[i]['slot']
                    if self._fitness(individual) < best:
                        best = self._fitness(individual)
                        improved = True
                        break
                    else:
                        individual[i]['slot'], individual[j]['slot'] = \
                            individual[j]['slot'], individual[i]['slot']
                if improved:
                    break
            iters += 1
        return individual

    def run(self) -> List[Dict]:
        print(" Запуск генетичного алгоритму...\n")

        population = [self._random_individual() for _ in range(self.pop_size)]
        best       = None
        best_score = float('inf')

        for gen in range(self.max_generations):
            scores  = [self._fitness(ind) for ind in population]
            cur_min = min(scores)
            if cur_min < best_score:
                best_score = cur_min
                best = copy.deepcopy(population[scores.index(cur_min)])

            self.log.append({
                'generation': gen,
                'best':       best_score,
                'avg':        np.mean(scores),
                'conflicts':  self._count_conflicts(best)
            })

            if gen % 100 == 0:
                print(f" Покоління {gen}: Score={best_score:.0f}, "
                      f"Конфлікти={self._count_conflicts(best)}")

            if self._count_conflicts(best) == 0:
                print(f"\n Розв'язок без конфліктів знайдено на поколінні {gen}!")
                break

            parents  = self._select(population, scores)
            children = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    c1, c2 = self._crossover(parents[i], parents[i+1])
                    children += [self._mutate(c1), self._mutate(c2)]

            combined        = population + children
            combined_scores = [self._fitness(x) for x in combined]
            population      = [x for x, _ in
                                sorted(zip(combined, combined_scores), key=lambda t: t[1])
                                [:self.pop_size]]

        print("\n Застосування локального пошуку (2-opt)...")
        best = self._local_search(best)

        print(f"\n Підсумок:")
        print(f"   Значення функції:    {self._fitness(best):.0f}")
        print(f"   Конфлікти:           {self._count_conflicts(best)}")
        print(f"   Вікна:               {self._count_gaps(best)}")
        return best


class ResultViewer:
    """Виведення та збереження результатів"""

    def __init__(self, data: InputData, scheduler: GeneticScheduler):
        self.data      = data
        self.scheduler = scheduler

    def print_timetable(self, schedule: List[Dict]):
        day_names = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"]
        print("\n" + "=" * 70)
        print("  РОЗКЛАД ЗАНЯТЬ".center(70))
        print("=" * 70)
        for day in range(self.data.days_count):
            print(f"\n{'─'*70}")
            print(f"  {day_names[day].upper()}")
            print(f"{'─'*70}")
            for pair in range(self.data.pairs_per_day):
                slot  = day * self.data.pairs_per_day + pair
                items = [e for e in schedule if e['slot'] == slot]
                if items:
                    print(f"\n  Пара {pair+1}:")
                    for item in items:
                        room = self.data.rooms[item['room_id']]
                        print(f"     {item['group_name']}: {item['course_name']} "
                              f"({item['kind']}) |  {item['teacher_name']} | "
                              f" {room['name']}")
        print("\n" + "=" * 70)

    def plot_convergence(self):
        df = pd.DataFrame(self.scheduler.log)
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.patch.set_facecolor('white')

        axes[0].plot(df['generation'], df['best'],
                     label='Найкраще', linewidth=3, color='#1565c0',
                     marker='o', markersize=4, markevery=50)
        axes[0].plot(df['generation'], df['avg'],
                     label='Середнє', linewidth=2, color='#ef6c00',
                     linestyle='--', alpha=0.7)
        axes[0].set_xlabel('Покоління', fontsize=13, fontweight='bold')
        axes[0].set_ylabel('Значення функції', fontsize=13, fontweight='bold')
        axes[0].set_title(f'Збіжність алгоритму (MODE={MODE})', fontsize=15, fontweight='bold')
        axes[0].legend(fontsize=12)
        axes[0].grid(True, alpha=0.3, linestyle='--')
        axes[0].set_facecolor('#f5f5f5')
        for sp in ['top', 'right']: axes[0].spines[sp].set_visible(False)

        axes[1].plot(df['generation'], df['conflicts'],
                     linewidth=3, color='#b71c1c',
                     marker='s', markersize=4, markevery=50)
        axes[1].set_xlabel('Покоління', fontsize=13, fontweight='bold')
        axes[1].set_ylabel('Кількість конфліктів', fontsize=13, fontweight='bold')
        axes[1].set_title('Динаміка конфліктів', fontsize=15, fontweight='bold')
        axes[1].grid(True, alpha=0.3, linestyle='--')
        axes[1].set_facecolor('#f5f5f5')
        for sp in ['top', 'right']: axes[1].spines[sp].set_visible(False)

        plt.tight_layout()
        plt.savefig('output/convergence.png', dpi=150, bbox_inches='tight')
        print(" Збережено: output/convergence.png")

    def plot_load(self, schedule: List[Dict]):
        day_labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт']

        by_day = [0] * self.data.days_count
        for e in schedule:
            by_day[e['slot'] // self.data.pairs_per_day] += 1

        by_teacher = [0] * self.data.teachers_count
        for e in schedule:
            by_teacher[e['teacher_id']] += 1

        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.patch.set_facecolor('white')

        b1 = axes[0].bar(day_labels, by_day, color='#388e3c',
                         alpha=0.85, edgecolor='#1b5e20', linewidth=2)
        axes[0].set_xlabel('День тижня', fontsize=13, fontweight='bold')
        axes[0].set_ylabel('Кількість занять', fontsize=13, fontweight='bold')
        axes[0].set_title('Навантаження по днях', fontsize=15, fontweight='bold')
        axes[0].grid(axis='y', alpha=0.3, linestyle='--')
        axes[0].set_facecolor('#f5f5f5')
        for sp in ['top', 'right']: axes[0].spines[sp].set_visible(False)
        for bar in b1:
            h = bar.get_height()
            axes[0].text(bar.get_x() + bar.get_width() / 2, h,
                         f'{int(h)}', ha='center', va='bottom', fontsize=12, fontweight='bold')

        b2 = axes[1].bar(range(self.data.teachers_count), by_teacher,
                         color='#e64a19', alpha=0.85, edgecolor='#bf360c', linewidth=2)
        axes[1].set_xlabel('ID викладача', fontsize=13, fontweight='bold')
        axes[1].set_ylabel('Кількість занять', fontsize=13, fontweight='bold')
        axes[1].set_title('Навантаження викладачів', fontsize=15, fontweight='bold')
        axes[1].grid(axis='y', alpha=0.3, linestyle='--')
        axes[1].set_facecolor('#f5f5f5')
        for sp in ['top', 'right']: axes[1].spines[sp].set_visible(False)
        for bar in b2:
            h = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2, h,
                         f'{int(h)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

        plt.tight_layout()
        plt.savefig('output/load_distribution.png', dpi=150, bbox_inches='tight')
        print(" Збережено: output/load_distribution.png")

    def print_report(self, schedule: List[Dict]):
        conflicts = self.scheduler._count_conflicts(schedule)
        gaps      = self.scheduler._count_gaps(schedule)
        pref_dev  = self.scheduler._count_pref_deviation(schedule)

        max_dev      = len(schedule) * self.data.slots_total
        satisfaction = (1 - pref_dev / max_dev) * 100
        status       = " ВІДСУТНІ" if conflicts == 0 else f"  {conflicts}"

        print("\n" + "=" * 60)
        print("  ПІДСУМКОВИЙ ЗВІТ".center(60))
        print("=" * 60)
        print(f"   Дата:   {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        print(f"   Режим:  MODE={MODE}")
        print(f"\n   ЯКІСТЬ РОЗКЛАДУ")
        print(f"  {'─'*40}")
        print(f"  Конфлікти ресурсів:       {status}")
        print(f"  Вікна у розкладі:          {gaps}")
        print(f"  Задоволеність викладачів:  {satisfaction:.1f}%")
        print(f"\n    ПАРАМЕТРИ")
        print(f"  {'─'*40}")
        print(f"  Викладачів:     {self.data.teachers_count}")
        print(f"  Дисциплін:      {self.data.courses_count}")
        print(f"  Аудиторій:      {self.data.rooms_count}")
        print(f"  Груп:           {self.data.groups_count}")
        print(f"\n   АЛГОРИТМ")
        print(f"  {'─'*40}")
        print(f"  Метод:             Генетичний алгоритм + Локальний пошук (2-opt)")
        print(f"  Розмір популяції:  {self.scheduler.pop_size}")
        print(f"  Виконано ітерацій: {len(self.scheduler.log)}")
        print("=" * 60)


def main():
    os.makedirs('output', exist_ok=True)

    print("=" * 60)
    print(" СКЛАДАННЯ РОЗКЛАДУ ЗАНЯТЬ КАФЕДРИ".center(60))
    print("=" * 60)

    print("\n  Підготовка даних...")
    data = InputData()
    print(f"   ✓ Викладачів: {data.teachers_count}")
    print(f"   ✓ Дисциплін:  {data.courses_count}")
    print(f"   ✓ Аудиторій:  {data.rooms_count}")
    print(f"   ✓ Груп:       {data.groups_count}")

    print("\n  Оптимізація...")
    scheduler = GeneticScheduler(data)
    result    = scheduler.run()

    print("\n  Виведення результатів...")
    viewer = ResultViewer(data, scheduler)
    viewer.print_report(result)
    viewer.print_timetable(result)
    viewer.plot_convergence()
    viewer.plot_load(result)

    out_path = 'output/schedule.csv'
    pd.DataFrame(result).to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n Розклад збережено: {os.path.abspath(out_path)}")

    print("\n" + "=" * 60)
    print("  ВИКОНАНО!".center(60))
    print("=" * 60)


if __name__ == "__main__":
    main()
