from typing import List

from loader import Inventory

DU_STMT = """
select
    common_prefix,
    sum(size) as size
from (
    select
        key,
        CASE cardinality(split(substr(key, length('{prefix}') + 1), '{delimiter}'))
            WHEN 1 THEN split_part(substr(key, length('{prefix}') + 1), '{delimiter}', 1)
            ELSE split_part(substr(key, length('{prefix}') + 1), '{delimiter}', 1) || '{delimiter}'
        END as common_prefix,
        size
    from {table_name}
    where
        dt = '{date}'
        and key like '{prefix}%'
        and (is_latest = true or is_latest is null)
        and (is_delete_marker = false or is_delete_marker is null)
)
group by common_prefix
order by size desc
"""


DU_DIFF_STMT = """
with one_day as (select
    common_prefix,
    sum(size) as total,
    dt
from (
    select
        key,
        CASE cardinality(split(substr(key, length('{prefix}') + 1), '{delimiter}'))
            WHEN 1 THEN split_part(substr(key, length('{prefix}') + 1), '{delimiter}', 1)
            ELSE split_part(substr(key, length('{prefix}') + 1), '{delimiter}', 1) || '{delimiter}'
        END as common_prefix,
        size,dt
    from {table_name}
    where
         key like '{prefix}%'
        and (is_latest = true or is_latest is null)
        and (is_delete_marker = false or is_delete_marker is null)
)
group by common_prefix,dt)

select
    common_prefix,
    d1.total as size_left,
    d2.total as size_right,
    d1.total - d2.total as diff
from
(select * from one_day where dt='{date_left}') d1 full outer join
(select * from one_day where dt='{date_right}') d2 using (common_prefix)
order by
    abs(diff) desc,
    size_left desc,
    size_right desc
"""


def size_for(db: Inventory, date: str, prefix: str = '', delimiter: str = '/') -> List[dict]:
    results = db.query(DU_STMT, prefix=prefix, delimiter=delimiter, date=date)
    return [{'common_prefix': r.get('common_prefix'), 'size': int(r.get('size'))} for r in results]


def diff_for(db: Inventory, date_left: str, date_right: str, prefix: str = '', delimiter: str = '/') -> List[dict]:
    results = db.query(DU_DIFF_STMT, prefix=prefix, delimiter=delimiter, date_left=date_left, date_right=date_right)
    adjusted = []
    for r in results:
        size_left = r.get('size_left')
        size_right = r.get('size_right')
        if not size_right:
            diff = size_left
        elif not size_left:
            diff = f'-{size_right}'
        else:
            diff = int(r.get('diff') or '0')
        adjusted.append({
            'common_prefix': r.get('common_prefix'),
            'size_left': int(r.get('size_left') or '0'),
            'size_right': int(r.get('size_right') or '0'),
            'diff': int(diff),
        })
    return adjusted
