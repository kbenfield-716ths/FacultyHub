class RunPayload(BaseModel):
    month: str      # "2025-12"
    strategy: str = "balanced"
    night_slots: int = 1


@app.post("/api/run_optimizer")
def run_optimizer(payload: RunPayload, db=Depends(get_db)):
    year, month = map(int, payload.month.split("-"))
    month_row = (
        db.query(Month)
        .filter(Month.year == year, Month.month == month)
        .first()
    )
    if not month_row:
        raise HTTPException(status_code=400, detail="No signups for that month")

    # Clear old assignments
    db.query(Assignment).join(Shift).filter(
        Shift.month_id == month_row.id
    ).delete(synchronize_session=False)

    assignments = run_optimizer_for_month(
        db=db,
        month_row=month_row,
        strategy=payload.strategy,
        night_slots=payload.night_slots,
    )

    # Persist
    for provider, shift in assignments:
        db.add(Assignment(provider_id=provider.id, shift_id=shift.id))

    db.commit()
    return {"status": "ok", "assigned": len(assignments)}
