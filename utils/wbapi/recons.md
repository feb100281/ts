## Делаем сверку с WB по разным датам

```sql
select t.*,
        son.name as son,
        dt.name as doc_type,
        pp.name as pmt_processing,
        nms.name as nm_name


        from wb_dwh.realization_kv t
        left join wb_dwh.dim_supplier_oper as son on son.id=t.son_id
        left join wb_dwh.payment_processing as pp on t.pmt_processing_id = pp.id
        left join wb_dwh.dim_doc_type as dt on dt.id = t.dtn_id
        left join public.sales_nms as nms on t.nm_id = nms.nm_id

        where t.sale_dt >='2026-02-21' and t.sale_dt < '2026-02-22'
```

__У WB 9633 записей__
__У WB 973 уникльных номенклатр__


По sales_dt 
- у нас 9685 , 988 - номенклатур

По date_from 
- у нас 9696, 990 - номенклатур

По rr_dt
- у нас 9696 записей, 990 номенклатур

По create_dt
- у нас 17407 записей 2282 - номенклатур

__Ничего не сошлось__

Количество по уникальным номенлатурам sale_dt

WB unique: 973
OUR unique: 988
Только в WB: 2
Только у нас: 17

Количество по уникальным номенлатурам rr_dt 

WB unique: 973
OUR unique: 990
Только в WB: 0
Только у нас: 17
Пересечение: 973


Количество по уникальным номенлатурам date_from

WB unique: 973
OUR unique: 990
Только в WB: 0
Только у нас: 17
Пересечение: 973


__БЕРЕМ `rr_dt`__

Ищем номенклатуры которые есть у нас а нет в WB и смотрим время продажи или другие анамалии




