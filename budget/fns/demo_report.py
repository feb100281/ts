# budget/fns/demo_report.py

from reporter_builder import Report, Section, P, T


def build_demo_report():
    # -----------------------------
    # Демо SVG
    # -----------------------------
    demo_svg = """
    <svg viewBox="0 0 700 220" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="700" height="220" fill="white"/>

      <line x1="60" y1="180" x2="660" y2="180" stroke="#D9E1E8" stroke-width="1"/>
      <line x1="60" y1="40" x2="60" y2="180" stroke="#D9E1E8" stroke-width="1"/>

      <rect x="110" y="95" width="80" height="85" fill="#1E3A5F" rx="4"/>
      <rect x="240" y="70" width="80" height="110" fill="#1E3A5F" rx="4"/>
      <rect x="370" y="120" width="80" height="60" fill="#1E3A5F" rx="4"/>
      <rect x="500" y="55" width="80" height="125" fill="#1E3A5F" rx="4"/>

      <text x="150" y="195" font-size="12" text-anchor="middle" fill="#4B5563">Q1</text>
      <text x="280" y="195" font-size="12" text-anchor="middle" fill="#4B5563">Q2</text>
      <text x="410" y="195" font-size="12" text-anchor="middle" fill="#4B5563">Q3</text>
      <text x="540" y="195" font-size="12" text-anchor="middle" fill="#4B5563">Q4</text>

      <text x="150" y="88" font-size="12" text-anchor="middle" fill="#243447">12.4</text>
      <text x="280" y="63" font-size="12" text-anchor="middle" fill="#243447">15.8</text>
      <text x="410" y="113" font-size="12" text-anchor="middle" fill="#243447">8.7</text>
      <text x="540" y="48" font-size="12" text-anchor="middle" fill="#243447">17.2</text>
    </svg>
    """

    plan_fact_columns = [
        {"key": "article", "label": "Статья"},
        {"key": "plan", "label": "План, ₽"},
        {"key": "fact", "label": "Факт, ₽"},
        {"key": "delta", "label": "Отклонение, ₽"},
        {"key": "delta_pct", "label": "Отклонение, %"},
    ]

    plan_fact_rows = [
        {
            "article": "Арендный доход",
            "plan": "12 000 000",
            "fact": "12 540 000",
            "delta": "+540 000",
            "delta_pct": "+4.5%",
        },
        {
            "article": "Эксплуатационные расходы",
            "plan": "3 400 000",
            "fact": "3 520 000",
            "delta": "+120 000",
            "delta_pct": "+3.5%",
        },
        {
            "article": "Административные расходы",
            "plan": "1 850 000",
            "fact": "1 790 000",
            "delta": "-60 000",
            "delta_pct": "-3.2%",
        },
        {
            "article": "Маркетинг",
            "plan": "600 000",
            "fact": "730 000",
            "delta": "+130 000",
            "delta_pct": "+21.7%",
        },
    ]

    tenant_columns = [
        {"key": "contr_name", "label": "Арендатор"},
        {"key": "agreement", "label": "Договор"},
        {"key": "premises", "label": "Тип помещения"},
        {"key": "map", "label": "МАП, ₽"},
    ]

    tenant_rows = [
        {
            "contr_name": "ООО «Альфа»",
            "agreement": "Д-101/25",
            "premises": "Офис",
            "map": "450 000",
        },
        {
            "contr_name": "ООО «Бета Логистик»",
            "agreement": "Д-118/25",
            "premises": "Склад",
            "map": "780 000",
        },
        {
            "contr_name": "ООО «Сити Парк»",
            "agreement": "Д-095/25",
            "premises": "Машино-места",
            "map": "210 000",
        },
    ]

    s1 = Section(1, "Ключевые выводы")
    s1.paragraph(
        "Исполнение бюджета за отчетный период оценивается как стабильное: основное отклонение связано с ростом маркетинговых расходов при сохранении положительной динамики по доходной части.",
        style=P.LEAD
    )
    s1.paragraph(
        "Выручка по арендным платежам превысила план, что частично компенсировало превышение бюджета по отдельным операционным статьям.",
        style=P.NORMAL
    )
    s1.paragraph(
        "Ниже приведены ключевые управленческие выводы по итогам месяца.",
        style=P.MUTED
    )
    s1.list(
        [
            "Арендный доход выше плана на 4.5%",
            "Основной перерасход сформирован в блоке маркетинга",
            "Административные расходы находятся ниже утвержденного уровня",
            "Общее отклонение остается в допустимом диапазоне"
        ],
        title="Краткое резюме"
    )
    s1.paragraph(
        "Отклонения рассчитаны относительно утвержденного бюджета месяца без учета последующих корректировок.",
        style=P.COMMENT
    )
    s1.paragraph(
        "Источник: управленческий контур, бюджетная модель, выгрузка по фактическим начислениям.",
        style=P.SMALL
    )

    s2 = Section(2, "Финансовая детализация")
    s2.paragraph(
        "Таблица ниже показывает сопоставление плановых и фактических значений по основным статьям бюджета.",
        style=P.MUTED
    )
    s2.table(
        columns=plan_fact_columns,
        rows=plan_fact_rows,
        title="План / факт по ключевым статьям",
        style=T.NO_BORDER
    )
    s2.paragraph(
        "Наиболее существенное отклонение наблюдается по статье маркетинга. При этом рост доходов от аренды компенсировал большую часть перерасхода.",
        style=P.NORMAL
    )
    s2.dict(
        {
            "Плановая выручка": "12 000 000 ₽",
            "Фактическая выручка": "12 540 000 ₽",
            "Отклонение по выручке": "+540 000 ₽",
            "Комментарий": "перевыполнение плана за счет индексаций и новых договоров"
        },
        title="Сводные показатели"
    )

    s3 = Section(3, "Визуализация")
    s3.paragraph(
        "Ниже приведен условный пример графического блока, который будет вставляться в отчет как SVG.",
        style=P.MUTED
    )
    s3.svg(
        content=demo_svg,
        title="Динамика квартальных поступлений",
        css_class="svg-center"
    )
    s3.paragraph(
        "Графический блок можно использовать для выручки, NOI, задолженности, индексаций или структуры портфеля.",
        style=P.COMMENT
    )
    s3.page_break()

    s4 = Section(4, "Портфель арендаторов")
    s4.paragraph(
        "Пример компактной таблицы по действующим договорам.",
        style=P.MUTED
    )
    s4.table(
        columns=tenant_columns,
        rows=tenant_rows,
        title="Действующие договоры",
        style=T.COMPACT
    )
    s4.paragraph(
        "В рабочих отчетах сюда можно выводить арендатор, договор, тип помещения, площадь, МАП, срок окончания и наличие просрочек.",
        style=P.SMALL
    )

    s5 = Section(5, "Следующий раздел после разрыва страницы")
    s5.paragraph(
        "Этот раздел начинается уже после page break. Так можно отделять приложения, большие таблицы или аналитические блоки.",
        style=P.LEAD
    )
    s5.list(
        [
            "Приложение 1: детализация по арендаторам",
            "Приложение 2: динамика ставок",
            "Приложение 3: просроченная задолженность"
        ],
        ordered=True,
        title="Состав приложений"
    )

    report = Report(
            title="Budget Report",
            subtitle="Финансовый обзор исполнения бюджета",
            company='ООО "ТРЕНДСЕТТЕР"',
            period="Январь 2026",
            author="Финансовый департамент",
            theme="executive",
            cover_title="Budget Report",
            cover_subtitle="Финансовый обзор исполнения бюджета",
            created_at="30.03.2026",
            show_cover=True,
            cover_type="Ежемесячный аналитический отчёт",
            cover_system="Financial & Performance Analysis",
            report_type="Ежемесячный",
            confidential=True
        )

    report.add(s1)
    report.add(s2)
    report.add(s3)
    report.add(s4)
    report.add(s5)

    return report.build()


a = build_demo_report()


if __name__ == "__main__":
    print(a)