from ninja import Router
from .services import ChlService

router = Router()

@router.get("/all.csv", tags=["Users"])    # must be before get/cruise_name
def getall(request):
    return ChlService.getall()

@router.get("/readme", response=str, tags=["Users"])
def get_readme(request):
    return ChlService.get_readme()

@router.get("/{cruise_name}.csv", tags=["Users"])
def get(request, cruise_name: str):
    return ChlService.get(cruise_name)



