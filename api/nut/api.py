from ninja import Router
from .services import NutService

router = Router()

@router.get("{cruise_id}")
def get(request, cruise_id: str):
    return NutService.get(cruise_id)


