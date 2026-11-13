from typing import *
from fastapi import FastAPI, HTTPException, Depends, Query, Response
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Center, Session
from schemas import (
CenterCreate, 
CenterOut, 
CenterWithSessions, 
SessionCreate, 
SessionOut
)

Base.metadata.create_all(bind = engine)

app = FastAPI()

@app.post("/centers", response_model = CenterOut, status_code = 201)
def create_center(center: CenterCreate, db: Session = Depends(get_db))-> CenterOut:

    a = Center(
        name = center.name,
        city = center.city
    )

    db.add(a)
    db.commit()
    db.refresh(a)

    return a

@app.post("/centers/{center_id}/sessions", response_model = SessionOut, status_code = 201)
def add_session(center_id: int, session: SessionCreate, db: Session = Depends(get_db))->SessionOut:

    b = db.query(Center).filter(Center.id == center_id).first()

    if b is None:
        raise HTTPException(
            status_code=404
        )
    
    c = Session(
        student_name = session.student_name,
        status = session.status,
        duration = session.duration,
        center_id = center_id
    )
    
    db.add(c)
    db.commit()
    db.refresh(c)

    return c

@app.get("/centers/{center_id}", response_model = CenterWithSessions, status_code = 200)
def get_center(center_id: int, status: Optional[str]=None, sort: Optional[str] = None, db: Session = Depends(get_db))-> CenterWithSessions:

    d = db.query(Center).filter(Center.id == center_id).first()

    if d is None:
        raise HTTPException(
            status_code=404,
            detail = "Center not found"
        )
    
    if sort is not None and sort not in ["student_name","duration"]:
        raise HTTPException(
            status_code=422
        )
    
    e = db.query(Session).filter(Session.center_id == center_id)

    if status is not None:
        e = e.filter(Session.status == status)

    if sort == "student_name":
        e = e.order_by(Session.student_name.asc())

    if sort == "duration":
        e = e.order_by(Session.duration.asc())

    ee = e.all()

    return CenterWithSessions(
        id = d.id,
        name = d.name,
        city = d.city,
        sessions = ee
    )

@app.delete("/centers/{center_id}", status_code = 204)
def delete_center(center_id: int, db:Session = Depends(get_db))-> None:

    e = db.query(Center).filter(Center.id == center_id).first()

    if e is None:
        raise HTTPException(
            status_code=404,
        )
    
    db.delete(e)
    db.commit()

    return Response(status_code = 204)

