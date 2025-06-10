from ninja import Router
from .services import ChlService

router = Router()

@router.get("/all", tags=["Users"])    # must be before get/cruise_name
def getall(request):
    return ChlService.getall()

@router.get("/{cruise_name}", tags=["Users"])
def get(request, cruise_name: str):
    return ChlService.get(cruise_name)


