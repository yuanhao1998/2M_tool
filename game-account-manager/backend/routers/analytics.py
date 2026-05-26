from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Account, DiamondRecord, DiamondSnapshot
from schemas import (
    OverviewResponse,
    ComparisonResponse,
    TrendPoint,
    AccountTrendResponse,
    LocationDistribution,
    GroupStat,
    AccountRanking,
    CalendarEntry,
    CrossStat,
    DiamondRecordResponse,
    LowPerformer,
)

router = APIRouter(tags=["analytics"])


def _calc_change_rate(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


@router.get("/analytics/overview", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)):
    total = db.query(func.sum(DiamondRecord.amount)).scalar() or 0
    total_records = db.query(func.count(DiamondRecord.id)).scalar() or 0
    entry_count = db.query(func.count(func.distinct(DiamondRecord.recorded_at))).scalar() or 0
    top = (
        db.query(DiamondRecord.location, func.sum(DiamondRecord.amount).label("s"))
        .filter(DiamondRecord.location != "")
        .group_by(DiamondRecord.location)
        .order_by(func.sum(DiamondRecord.amount).desc())
        .first()
    )
    return OverviewResponse(
        total_diamonds=total,
        total_records=total_records,
        entry_count=entry_count,
        top_location=top[0] if top else None,
    )


@router.get("/analytics/overview/comparison", response_model=ComparisonResponse)
def overview_comparison(db: Session = Depends(get_db)):
    dates = (
        db.query(DiamondRecord.recorded_at)
        .distinct()
        .order_by(DiamondRecord.recorded_at.desc())
        .limit(2)
        .all()
    )
    if len(dates) < 2:
        current = (
            db.query(func.sum(DiamondRecord.amount))
            .filter(DiamondRecord.recorded_at == dates[0][0])
            .scalar()
        ) or 0 if dates else 0
        return ComparisonResponse(current_amount=current, previous_amount=0, change=0, change_rate=0.0)
    current = (
        db.query(func.sum(DiamondRecord.amount))
        .filter(DiamondRecord.recorded_at == dates[0][0])
        .scalar()
    ) or 0
    previous = (
        db.query(func.sum(DiamondRecord.amount))
        .filter(DiamondRecord.recorded_at == dates[1][0])
        .scalar()
    ) or 0
    return ComparisonResponse(
        current_amount=current,
        previous_amount=previous,
        change=current - previous,
        change_rate=_calc_change_rate(current, previous),
    )


@router.get("/analytics/overview/yoy", response_model=ComparisonResponse)
def overview_yoy(db: Session = Depends(get_db)):
    today = date.today()
    current_month = today.month
    current_year = today.year
    current_amount = (
        db.query(func.sum(DiamondRecord.amount))
        .filter(
            func.strftime("%m", DiamondRecord.recorded_at) == f"{current_month:02d}",
            func.strftime("%Y", DiamondRecord.recorded_at) == str(current_year),
        )
        .scalar()
    ) or 0
    prev_amount = (
        db.query(func.sum(DiamondRecord.amount))
        .filter(
            func.strftime("%m", DiamondRecord.recorded_at) == f"{current_month:02d}",
            func.strftime("%Y", DiamondRecord.recorded_at) == str(current_year - 1),
        )
        .scalar()
    ) or 0
    return ComparisonResponse(
        current_amount=current_amount,
        previous_amount=prev_amount,
        change=current_amount - prev_amount,
        change_rate=_calc_change_rate(current_amount, prev_amount),
    )


@router.get("/analytics/by-location", response_model=list[LocationDistribution])
def by_location(db: Session = Depends(get_db)):
    rows = (
        db.query(
            DiamondRecord.location,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .filter(DiamondRecord.location != "")
        .group_by(DiamondRecord.location)
        .order_by(func.sum(DiamondRecord.amount).desc())
        .all()
    )
    return [LocationDistribution(location=r[0], total_amount=r[1]) for r in rows]


@router.get("/analytics/by-server", response_model=list[GroupStat])
def by_server(
    recorded_at: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            Account.server,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .join(DiamondRecord, Account.id == DiamondRecord.account_id)
        .filter(Account.server != "")
    )
    if recorded_at:
        q = q.filter(DiamondRecord.recorded_at == recorded_at)
    rows = q.group_by(Account.server).order_by(func.sum(DiamondRecord.amount).desc()).all()
    return [GroupStat(name=r[0], total_amount=r[1]) for r in rows]


@router.get("/analytics/by-class", response_model=list[GroupStat])
def by_class(
    recorded_at: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            Account.class_name,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .join(DiamondRecord, Account.id == DiamondRecord.account_id)
        .filter(Account.class_name != "")
    )
    if recorded_at:
        q = q.filter(DiamondRecord.recorded_at == recorded_at)
    rows = q.group_by(Account.class_name).order_by(func.sum(DiamondRecord.amount).desc()).all()
    return [GroupStat(name=r[0], total_amount=r[1]) for r in rows]


@router.get("/analytics/by-location/{location}/trend", response_model=list[TrendPoint])
def location_trend(location: str, db: Session = Depends(get_db)):
    rows = (
        db.query(
            DiamondRecord.recorded_at,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .filter(DiamondRecord.location == location)
        .group_by(DiamondRecord.recorded_at)
        .order_by(DiamondRecord.recorded_at.asc())
        .all()
    )
    result = []
    for i, (d, amt) in enumerate(rows):
        prev = rows[i - 1][1] if i > 0 else None
        rate = _calc_change_rate(amt, prev) if prev and prev > 0 else None
        result.append(TrendPoint(date=d, amount=amt, change_rate=rate))
    return result


@router.get("/analytics/accounts/{account_id}/trend", response_model=AccountTrendResponse)
def account_trend(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    rows = (
        db.query(
            DiamondRecord.recorded_at,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .filter(DiamondRecord.account_id == account_id)
        .group_by(DiamondRecord.recorded_at)
        .order_by(DiamondRecord.recorded_at.asc())
        .all()
    )
    trend = []
    for i, (d, amt) in enumerate(rows):
        prev = rows[i - 1][1] if i > 0 else None
        rate = _calc_change_rate(amt, prev) if prev and prev > 0 else None
        trend.append(TrendPoint(date=d, amount=amt, change_rate=rate))
    return AccountTrendResponse(account_id=account_id, account_name=account.account_name, trend=trend)


# 1. 按大区统计
@router.get("/analytics/by-region", response_model=list[GroupStat])
def by_region(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Account.region,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .join(DiamondRecord, Account.id == DiamondRecord.account_id)
        .filter(Account.region != "")
        .group_by(Account.region)
        .order_by(func.sum(DiamondRecord.amount).desc())
        .all()
    )
    return [GroupStat(name=r[0], total_amount=r[1]) for r in rows]


# 2. 账号收益排行
@router.get("/analytics/account-ranking", response_model=list[AccountRanking])
def account_ranking(
    limit: int = Query(default=20),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            DiamondRecord.account_id,
            Account.account_name,
            Account.cloud_device,
            func.sum(DiamondRecord.amount).label("s"),
            func.count(DiamondRecord.id).label("c"),
        )
        .join(Account, Account.id == DiamondRecord.account_id)
    )
    if start_date:
        q = q.filter(DiamondRecord.recorded_at >= start_date)
    if end_date:
        q = q.filter(DiamondRecord.recorded_at <= end_date)
    rows = (
        q.group_by(DiamondRecord.account_id, Account.account_name, Account.cloud_device)
        .order_by(func.sum(DiamondRecord.amount).desc())
        .limit(limit)
        .all()
    )
    return [
        AccountRanking(account_id=r[0], account_name=r[1], cloud_device=r[2], total_amount=r[3], record_count=r[4])
        for r in rows
    ]


# 3. 按日趋势
@router.get("/analytics/daily-trend", response_model=list[TrendPoint])
def daily_trend(db: Session = Depends(get_db)):
    rows = (
        db.query(
            DiamondRecord.recorded_at,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .group_by(DiamondRecord.recorded_at)
        .order_by(DiamondRecord.recorded_at.asc())
        .all()
    )
    result = []
    for i, (d, amt) in enumerate(rows):
        prev = rows[i - 1][1] if i > 0 else None
        rate = _calc_change_rate(amt, prev) if prev and prev > 0 else None
        result.append(TrendPoint(date=d, amount=amt, change_rate=rate))
    return result


@router.get("/analytics/diamond-trend", response_model=list[TrendPoint])
def diamond_trend(db: Session = Depends(get_db)):
    rows = (
        db.query(
            DiamondSnapshot.date,
            func.sum(DiamondSnapshot.change).label("s"),
        )
        .group_by(DiamondSnapshot.date)
        .order_by(DiamondSnapshot.date.asc())
        .all()
    )
    result = []
    for i, (d, amt) in enumerate(rows):
        prev = rows[i - 1][1] if i > 0 else None
        rate = _calc_change_rate(amt, prev) if prev and prev > 0 else None
        result.append(TrendPoint(date=d, amount=amt, change_rate=rate))
    return result


# 3b. 按周趋势
@router.get("/analytics/weekly-trend", response_model=list[TrendPoint])
def weekly_trend(db: Session = Depends(get_db)):
    rows = (
        db.query(
            func.strftime("%Y-W%W", DiamondRecord.recorded_at).label("w"),
            func.sum(DiamondRecord.amount).label("s"),
        )
        .group_by("w")
        .order_by("w")
        .all()
    )
    result = []
    for i, (w, amt) in enumerate(rows):
        prev = rows[i - 1][1] if i > 0 else None
        rate = _calc_change_rate(amt, prev) if prev and prev > 0 else None
        parts = w.split("-W")
        from datetime import date as dt_date
        d = dt_date.fromisocalendar(int(parts[0]), int(parts[1]), 1)
        result.append(TrendPoint(date=d, amount=amt, change_rate=rate))
    return result


# 4. 日历热力图数据
@router.get("/analytics/calendar", response_model=list[CalendarEntry])
def calendar_data(
    year: int = Query(default=0),
    db: Session = Depends(get_db),
):
    from datetime import date as dt_date
    y = year if year else dt_date.today().year
    rows = (
        db.query(
            DiamondRecord.recorded_at,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .filter(
            func.strftime("%Y", DiamondRecord.recorded_at) == str(y)
        )
        .group_by(DiamondRecord.recorded_at)
        .all()
    )
    return [CalendarEntry(date=r[0], amount=r[1]) for r in rows]


# 5. 单账号对比（含全体均值）
@router.get("/analytics/accounts/{account_id}/trend-compare")
def account_trend_compare(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # 该账号按日趋势
    rows = (
        db.query(
            DiamondRecord.recorded_at,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .filter(DiamondRecord.account_id == account_id)
        .group_by(DiamondRecord.recorded_at)
        .order_by(DiamondRecord.recorded_at.asc())
        .all()
    )

    # 全体日均值
    all_dates = (
        db.query(DiamondRecord.recorded_at)
        .distinct()
        .order_by(DiamondRecord.recorded_at.asc())
        .all()
    )
    total_per_date = {}
    for (d,) in all_dates:
        total = (
            db.query(func.sum(DiamondRecord.amount))
            .filter(DiamondRecord.recorded_at == d)
            .scalar()
        ) or 0
        account_count = (
            db.query(func.count(func.distinct(DiamondRecord.account_id)))
            .filter(DiamondRecord.recorded_at == d)
            .scalar()
        ) or 1
        total_per_date[d] = total / account_count

    trend = []
    for i, (d, amt) in enumerate(rows):
        prev = rows[i - 1][1] if i > 0 else None
        rate = _calc_change_rate(amt, prev) if prev and prev > 0 else None
        trend.append({
            "date": d,
            "amount": amt,
            "change_rate": rate,
            "average": round(total_per_date.get(d, 0), 1),
        })

    return {
        "account_id": account_id,
        "account_name": account.account_name,
        "trend": trend,
    }


# 6. 区服 × 大区交叉统计
@router.get("/analytics/server-region-cross", response_model=list[CrossStat])
def server_region_cross(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Account.server,
            Account.region,
            func.sum(DiamondRecord.amount).label("s"),
        )
        .join(DiamondRecord, Account.id == DiamondRecord.account_id)
        .filter(Account.server != "", Account.region != "")
        .group_by(Account.server, Account.region)
        .order_by(func.sum(DiamondRecord.amount).desc())
        .all()
    )
    return [CrossStat(server=r[0], region=r[1], total_amount=r[2]) for r in rows]


# 7. 需关注账户（收益低于均值百分比）
@router.get("/analytics/low-performers", response_model=list[LowPerformer])
def low_performers(
    recorded_at: date | None = Query(default=None),
    threshold: float = Query(default=0.5),
    db: Session = Depends(get_db),
):
    # 每个账号收益
    sq = (
        db.query(
            DiamondRecord.account_id,
            func.sum(DiamondRecord.amount).label("s"),
        )
    )
    if recorded_at:
        sq = sq.filter(DiamondRecord.recorded_at == recorded_at)
    sq = sq.group_by(DiamondRecord.account_id).subquery()

    # 均值
    avg_row = db.query(func.avg(sq.c.s)).scalar()
    avg = float(avg_row or 0)
    if avg == 0:
        return []

    rows = (
        db.query(
            sq.c.account_id,
            Account.account_name,
            Account.cloud_device,
            sq.c.s,
        )
        .join(Account, Account.id == sq.c.account_id)
        .filter(sq.c.s < avg * threshold)
        .order_by(sq.c.s.asc())
        .all()
    )
    return [
        LowPerformer(
            account_id=r[0], account_name=r[1], cloud_device=r[2],
            total_amount=r[3], average=round(avg, 1), ratio=round(r[3] / avg * 100, 1),
        )
        for r in rows
    ]


@router.get("/analytics/records")
def analytics_records(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    location: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(DiamondRecord)
    if start_date:
        query = query.filter(DiamondRecord.recorded_at >= start_date)
    if end_date:
        query = query.filter(DiamondRecord.recorded_at <= end_date)
    if account_id:
        query = query.filter(DiamondRecord.account_id == account_id)
    if location:
        query = query.filter(DiamondRecord.location.ilike(f"%{location}%"))
    records = query.order_by(DiamondRecord.recorded_at.desc()).all()
    return [
        DiamondRecordResponse(
            id=r.id, account_id=r.account_id, amount=r.amount,
            location=r.location, recorded_at=r.recorded_at, account=r.account,
        )
        for r in records
    ]
