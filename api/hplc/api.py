from ninja import Router
from .services import HplcService

router = Router()

@router.get("/readme", response=str, tags=["Users"])
def get_readme(request):
    return HplcService.get_readme()

@router.get("/{cruise_name}", tags=["Users"])
def get(request, cruise_name: str):
    return HplcService.get(cruise_name)


