from ninja import Router
from .services import NutService

router = Router()

@router.get("/{cruise_name}", tags=["Users"])
def get(request, cruise_name: str):
    return NutService.get(cruise_name)


