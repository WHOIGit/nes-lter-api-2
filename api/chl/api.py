from ninja import Router
from .services import ChlService

router = Router()

@router.get("/{cruise_name}", tags=["Users"])
def get(request, cruise_name: str):
    return ChlService.get(cruise_name)


