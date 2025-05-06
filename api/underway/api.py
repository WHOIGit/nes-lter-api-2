from typing import List
from datetime import datetime
from ninja import Router
from .services import UnderwayService, UnderwayOutput
from pydantic import BaseModel, Field, validator

router = Router()

@router.get("/get/{cruise_name}", tags=["Users"])
def get_underway_data(request, cruise_name: str):
    return UnderwayService.get_data(cruise_name)

@router.get("/get_column_headers/{cruise_name}", tags=["Users"])
def get_underway_column_headers(request, cruise_name: str):
    return UnderwayService.get_column_headers(cruise_name)

@router.get("/find/{start_timestamp}/{end_timestamp}", response=List[UnderwayOutput], tags=["Users"])
def find_underway_files(request, start_timestamp: datetime, end_timestamp: datetime ):
    return UnderwayService.find_underway_files(start_timestamp, end_timestamp)



    


