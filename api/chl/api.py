from ninja import Router
from .services import ChlService

router = Router()

@router.get("{cruise_id}")
def get(request, cruise_id: str):
    return ChlService.get(cruise_id)


