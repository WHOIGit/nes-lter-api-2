from ninja import Router
from .services import HplcService

router = Router()

@router.get("/{cruise_name}", tags=["Users"])
def get(request, cruise_name: str):
    return HplcService.get(cruise_name)


