from fastapi.responses import PlainTextResponse
import io
import csv

@app.get("/api/schedule.csv", response_class=PlainTextResponse)
def get_schedule(month: str, db=Depends(get_db)):
    year, m = map(int, month.split("-"))
    month_row = (
        db.query(Month)
        .filter(Month.year == year, Month.month == m)
        .first()
    )
    if not month_row:
        raise HTTPException(status_code=400, detail="No assignments")

    rows = (
        db.query(Assignment, Provider, Shift)
        .join(Provider, Assignment.provider_id == Provider.id)
        .join(Shift, Assignment.shift_id == Shift.id)
        .order_by(Shift.date, Provider.name)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "provider_id", "provider_name"])
    for assignment, provider, shift in rows:
        writer.writerow([shift.date.isoformat(), provider.id, provider.name])

    return buf.getvalue()
