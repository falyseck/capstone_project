from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import auth
import models as m
import schemas as s
from database import get_db

router = APIRouter()


@router.get("/facilities", response_model=List[s.FacilityOut])
def list_facilities(db: Session = Depends(get_db)):
    return db.query(m.Facility).all()


@router.post("/auth/register", response_model=s.UserOut, status_code=201)
def register(payload: s.UserRegister, db: Session = Depends(get_db)):
    if db.query(m.User).filter(m.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    if not db.query(m.Facility).filter(m.Facility.id == payload.facility_id).first():
        raise HTTPException(status_code=400, detail="Facility not found.")

    user = m.User(
        name=payload.name,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role=m.RoleEnum(payload.role),
        facility_id=payload.facility_id,
        date_of_birth=payload.date_of_birth,
        delivery_date=payload.delivery_date,
        license_id=payload.license_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=s.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(m.User).filter(m.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token = auth.create_access_token({"sub": user.id, "role": user.role.value})
    return s.Token(access_token=token, role=user.role.value, user_id=user.id, name=user.name)
