from ninja import Router

router = Router()

@router.get("/")
def stations_root(request):
    return {"message": "Welcome to the stations API"}
