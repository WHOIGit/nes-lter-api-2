from ninja import Router

router = Router()

@router.get("/")
def core_root(request):
    return {"message": "Welcome to the core API"}
