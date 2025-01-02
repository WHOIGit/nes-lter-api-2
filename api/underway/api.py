from typing import List
from datetime import datetime
from ninja import Router
from django.http import FileResponse, Http404, JsonResponse
from .services import UnderwayService, UnderwayOutput

router = Router()


@router.get("read/{cruise_name}")
def read_underway_data(request, cruise_name: str):
    service = UnderwayService()
    return service.read_data(cruise_name)

@router.get("get/{cruise_name}")
def get_underway_data(request, cruise_name: str):
    return UnderwayService.get_data(cruise_name)

@router.get("get_column_headers/{cruise_name}")
def get_underway_column_headers(request, cruise_name: str):
    return UnderwayService.get_column_headers(cruise_name)

@router.get("find/{month}/{year}", response=List[UnderwayOutput])   #fix
def find_underway_files(request, month: int, year: int):
    return UnderwayService.find_underway_files(month, year)



    


