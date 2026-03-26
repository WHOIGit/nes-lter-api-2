from ninja import Router
from .services import NutService

router = Router()

@router.get("/all.csv", tags=["Users"])    # must be before get/cruise_name
def getall(request):
    return NutService.getall()

@router.get("/readme", response=str, tags=["Users"])
def get_readme(request):
    return NutService.get_readme()

@router.get("/ar52_nutrient_samplelog.csv", tags=["Users"])
def get_ar52_nutrient_samplelog(request):
    return NutService.ar52_nutrient_samplelog()

@router.get("/{cruise_name}.csv", tags=["Users"])
def get(request, cruise_name: str):
    return NutService.get(cruise_name)



