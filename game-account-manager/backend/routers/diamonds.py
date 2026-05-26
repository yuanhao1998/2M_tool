from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Account, DiamondSnapshot, DiamondSale, DiamondRecord
from schemas import (
    DiamondSyncRequest, DiamondSyncResponse,
    DiamondSellRequest, DiamondSellResponse,
    DiamondSaleResponse, DiamondSnapshotResponse,
)

router = APIRouter(tags=["diamonds"])


@router.post("/diamonds/sync", response_model=DiamondSyncResponse)
def sync_diamonds(data: DiamondSyncRequest, db: Session = Depends(get_db)):
    today = date.today()
    updated = 0
    snapshots_created = 0

    for item in data.updates:
        account = db.query(Account).filter(Account.cloud_device == item.cloud_device.strip()).first()
        if not account:
            continue

        new_diamonds = item.diamonds
        account.current_diamonds = new_diamonds
        updated += 1

        last_before = (
            db.query(DiamondSnapshot)
            .filter(
                DiamondSnapshot.account_id == account.id,
                DiamondSnapshot.date < today,
            )
            .order_by(DiamondSnapshot.date.desc())
            .first()
        )
        prev_diamonds = last_before.diamonds if last_before else 0
        last_date = last_before.date if last_before else None

        # Account for sales between last snapshot and today
        sold_since = 0
        if last_date:
            sold_since = (
                db.query(DiamondSale)
                .filter(
                    DiamondSale.account_id == account.id,
                    DiamondSale.sale_date > last_date,
                    DiamondSale.sale_date <= today,
                )
                .count()
            )
        # total production = current - prev + all diamonds sold since last snapshot
        total_change = new_diamonds - prev_diamonds
        if sold_since > 0:
            total_sold_diamonds = (
                db.query(DiamondSale)
                .filter(
                    DiamondSale.account_id == account.id,
                    DiamondSale.sale_date > last_date,
                    DiamondSale.sale_date <= today,
                )
                .with_entities(func.sum(DiamondSale.diamonds_sold))
                .scalar()
            ) or 0
            total_change += total_sold_diamonds

        existing_today = (
            db.query(DiamondSnapshot)
            .filter(
                DiamondSnapshot.account_id == account.id,
                DiamondSnapshot.date == today,
            )
            .first()
        )

        if existing_today:
            # Same day re-sync: accumulate the incremental change
            old_diamonds = existing_today.diamonds
            existing_today.diamonds = new_diamonds
            existing_today.change += new_diamonds - old_diamonds
        elif last_date and last_date < today - timedelta(days=1):
            # Gap between last snapshot and today: distribute change evenly
            num_days = (today - last_date).days
            per_day = total_change // num_days
            extra = total_change % num_days

            current = last_date + timedelta(days=1)
            while current <= today:
                day_change = per_day + (1 if extra > 0 else 0)
                if extra > 0:
                    extra -= 1

                existed = (
                    db.query(DiamondSnapshot)
                    .filter(
                        DiamondSnapshot.account_id == account.id,
                        DiamondSnapshot.date == current,
                    )
                    .first()
                )
                if existed:
                    existed.change += day_change
                    if current == today:
                        existed.diamonds = new_diamonds
                else:
                    snapshot = DiamondSnapshot(
                        account_id=account.id,
                        date=current,
                        diamonds=new_diamonds if current == today else 0,
                        change=day_change,
                    )
                    db.add(snapshot)
                    snapshots_created += 1
                current += timedelta(days=1)
        else:
            # First sync, or consecutive day: normal snapshot
            snapshot = DiamondSnapshot(
                account_id=account.id,
                date=today,
                diamonds=new_diamonds,
                change=total_change,
            )
            db.add(snapshot)
            snapshots_created += 1

    db.commit()
    return DiamondSyncResponse(updated_count=updated, snapshot_count=snapshots_created)


@router.post("/diamonds/sell", response_model=DiamondSellResponse)
def sell_diamonds(data: DiamondSellRequest, db: Session = Depends(get_db)):
    today = date.today()
    sold_count = 0
    total_sold = 0

    for account_id in data.account_ids:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account or account.current_diamonds <= 0:
            continue

        diamonds_to_sell = account.current_diamonds

        sale = DiamondSale(
            account_id=account.id,
            diamonds_sold=diamonds_to_sell,
            sale_date=today,
        )
        db.add(sale)

        record = DiamondRecord(
            account_id=account.id,
            amount=diamonds_to_sell,
            location="",
            recorded_at=today,
        )
        db.add(record)

        account.current_diamonds = 0
        sold_count += 1
        total_sold += diamonds_to_sell

    db.commit()
    return DiamondSellResponse(sold_count=sold_count, total_diamonds_sold=total_sold)


@router.get("/diamonds/sales", response_model=list[DiamondSaleResponse])
def list_sales(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            DiamondSale.id,
            DiamondSale.account_id,
            Account.account_name,
            Account.cloud_device,
            Account.phone,
            DiamondSale.diamonds_sold,
            DiamondSale.sale_date,
            DiamondSale.created_at,
        )
        .join(Account, Account.id == DiamondSale.account_id)
    )
    if start_date:
        query = query.filter(DiamondSale.sale_date >= start_date)
    if end_date:
        query = query.filter(DiamondSale.sale_date <= end_date)
    if account_id:
        query = query.filter(DiamondSale.account_id == account_id)

    rows = query.order_by(DiamondSale.created_at.desc()).all()
    return [
        DiamondSaleResponse(
            id=r[0], account_id=r[1], account_name=r[2],
            cloud_device=r[3], phone=r[4], diamonds_sold=r[5],
            sale_date=r[6], created_at=r[7],
        )
        for r in rows
    ]


@router.get("/accounts/{account_id}/diamond-snapshots", response_model=list[DiamondSnapshotResponse])
def account_diamond_snapshots(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return (
        db.query(DiamondSnapshot)
        .filter(DiamondSnapshot.account_id == account_id)
        .order_by(DiamondSnapshot.date.desc())
        .all()
    )
