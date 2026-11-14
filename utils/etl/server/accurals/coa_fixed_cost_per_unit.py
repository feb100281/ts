import psycopg
from psycopg.rows import dict_row

    

def insert_accurals(conn, **args):
    param = args.get('param_json') or {}
    

    cost_per_unit = eval(param.get('Средняя стоимость ед', '0'))
    margin = eval(param.get('Дефолтная маржа проц', '0'))

    pl_acc = args.get('acc_pl_id', None)
    pl_subconto = args.get('subconto_pl_id', None)
    bs_acc = args.get('acc_bs_id', None)
    bs_subconto = args.get('subconto_bs_id', None)
    company_id = 1
    
    sql_params = (
        cost_per_unit,
        cost_per_unit,
        margin,
        bs_acc,
        bs_subconto,
        company_id,
        pl_acc,
        pl_subconto,
        company_id      
    )

    SQL = """
    with src as (
    SELECT
        a.date_from,
        a.revenue,
        COALESCE(a.quant, 0) AS quant,
        a.defalt_margin,
        (
            a.revenue * (a.defalt_margin / 100.0)
            + COALESCE(a.quant, 0) * %s * 100
        )::bigint AS write_off_cost,
        CASE
            WHEN a.defalt_margin = 0 THEN
                concat_ws(
                    ' ',
                    'Списание на себестоимость',
                    COALESCE(a.quant, 0)::bigint,
                    'ед товара по средней с/с',
                    %s,
                    'руб/ед'
                )
            ELSE
                concat_ws(
                    ' ',
                    'Списание на себестоимость по средней марже',
                    a.defalt_margin,
                    '%%'
                )
        END AS description
    FROM(
    SELECT
    x.date_from,
    x.revenue,
    t.quant,
    CASE when t.quant is null then %s else 0 end as defalt_margin
    FROM (
    select 
    date_from,
    sum(cr-dt)::bigint as revenue
    from gl.fact 
    where acc_id = 48 
    group by date_from

    ) x
    left join gl.wb_quant as t on t.date_from = x.date_from
    ) a
    order by date_from
    ),
    gl_format as (
    select
    gen_random_uuid()::uuid as id,
    null::uuid as pid,
    date_from::date as date_from,
    %s::bigint as acc_id,
    null::bigint as contract_id,
    0::bigint as dt,
    write_off_cost::bigint as cr,
    description::text as description,
    %s::bigint as subconto_id,
    %s::bigint as company_id,
    'BS_write_off'::text as chapter
    from src

    union all

    select
    gen_random_uuid()::uuid as id,
    null::uuid as pid,
    date_from::date as date_from,
    %s::bigint as acc_id,
    null::bigint as contract_id,
    write_off_cost::bigint as dt,
    0::bigint as cr,
    description::text as description,
    %s::bigint as subconto_id,
    %s::bigint as company_id,
    'PL_write_off'::text as chapter
    from src 
    

    ),

    src_m AS (

        SELECT * 
        FROM gl_format where acc_id is not null

        UNION ALL

        SELECT
            gen_random_uuid()::uuid      AS id,
            NULL::uuid                   AS pid,
            t.date::date                 AS date_from,
            t.acc_id::bigint             AS acc_id,
            t.contract_id::bigint        AS contract_id,
            round(t.dt * 100, 0)::bigint AS dt,
            round(t.cr * 100, 0)::bigint AS cr,
            t.temp::text                 AS description,
            t.cfitem_id::bigint          AS subconto_id,
            t.owner_id::bigint           AS company_id,
            'MANUAL_TRS'::text           AS chapter
        FROM public.grossbook_manual t
        WHERE EXISTS (
            SELECT 1
            FROM gl_format g
            WHERE g.acc_id = t.acc_id
        )
    ),

    filtered AS (
        SELECT *
        FROM src_m s
        WHERE COALESCE(s.dt, 0) <> 0
        OR COALESCE(s.cr, 0) <> 0
    )
    INSERT INTO gl.fact (
        id,
        pid,
        date_from,
        acc_id,
        contract_id,
        dt,
        cr,
        description,
        subconto_id,
        company_id,
        chapter
    )
    SELECT
        id,
        pid,
        date_from,
        acc_id,
        contract_id,
        dt,
        cr,
        description,
        subconto_id,
        company_id,
        chapter
    FROM filtered
    ON CONFLICT (id) DO UPDATE
    SET
        pid         = EXCLUDED.pid,
        date_from   = EXCLUDED.date_from,
        acc_id      = EXCLUDED.acc_id,
        contract_id = EXCLUDED.contract_id,
        dt          = EXCLUDED.dt,
        cr          = EXCLUDED.cr,
        description = EXCLUDED.description,
        subconto_id = EXCLUDED.subconto_id,
        company_id  = EXCLUDED.company_id,
        chapter     = EXCLUDED.chapter
    WHERE
        (gl.fact.pid,
        gl.fact.date_from,
        gl.fact.acc_id,
        gl.fact.contract_id,
        gl.fact.dt,
        gl.fact.cr,
        gl.fact.description,
        gl.fact.subconto_id,
        gl.fact.company_id,
        gl.fact.chapter)
    IS DISTINCT FROM
        (EXCLUDED.pid,
        EXCLUDED.date_from,
        EXCLUDED.acc_id,
        EXCLUDED.contract_id,
        EXCLUDED.dt,
        EXCLUDED.cr,
        EXCLUDED.description,
        EXCLUDED.subconto_id,
        EXCLUDED.company_id,
        EXCLUDED.chapter);
    """
    
    print(sql_params)
    with conn.cursor() as cur:
        cur.execute(SQL,sql_params)
        
    for k, v in args.items():
        print(k, "=", v)
    
    print(param)
    print(sql_params)

    conn.commit()

    return 'ALL GOOD AND INSERT COA AV PER UNIT'


def main(conn, **args):
    print(insert_accurals(conn,**args))


if __name__ == "__main__":
    main()