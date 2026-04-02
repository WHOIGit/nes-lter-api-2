from typing import List
from ninja import Router
from .services import UnderwayService, UnderwayOutput

router = Router()

@router.get("/column_definition/{cruise_name}.csv", tags=["Users"])
def get_column_definition_csv(request, cruise_name: str):
    return UnderwayService.get_column_definition_csv(cruise_name)

@router.get("/column_definition/{cruise_name}", tags=["Users"])
def get_column_definition(request, cruise_name: str):
    return UnderwayService.get_column_definition(cruise_name)


@router.get("/{cruise_name}.csv", tags=["Users"])
def get_underway_data(request, cruise_name: str):
    return UnderwayService.get_data(cruise_name)

@router.get("/get_column_headers/{cruise_name}", tags=["Users"])
def get_underway_column_headers(request, cruise_name: str):
    return UnderwayService.get_column_headers(cruise_name)

@router.get("/find/{start_timestamp}/{end_timestamp}", response=List[UnderwayOutput], tags=["Users"])
def find_underway_files(request, start_timestamp: str, end_timestamp: str ):
    return UnderwayService.find_underway_files(start_timestamp, end_timestamp)

@router.get("/readme/{cruise_name}", response=str, tags=["Users"])
def get_readme(request, cruise_name: str):
    return UnderwayService.get_readme(cruise_name)




    


