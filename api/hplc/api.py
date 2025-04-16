from ninja import Router
from .services import HplcService

router = Router()

@router.get("{cruise_id}")
def get(request, cruise_id: str):
    return HplcService.get(cruise_id)


