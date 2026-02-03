from typing import List
from ninja import Router
from core.auth import TokenAuthenticator

from .services import CtdService, NiskinInput, VesselOutput, AddVesselInput, \
    UpdateVesselInput, CruiseOutput, AddCruiseInput,  \
    UpdateCruiseInput, CastOutput, CastInput, UpdateCastInput, \
    NiskinInput, NiskinOutput, UpdateNiskinInput

router = Router()

@router.get("/vessels/all", response=List[VesselOutput], tags=["Users"])
def get_vessels(request):
    return CtdService.get_vessels()

@router.post('/vessels/create', tags=["Admin"], auth=TokenAuthenticator())
def create_vessel(request, input: AddVesselInput):
    try:
        new_vessel = CtdService.create_vessel(input)
        return {"status": "success", "vessel": new_vessel}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.post('/vessels/update/{vessel_name}', tags=["Admin"], auth=TokenAuthenticator())
def update_vessel(request, vessel_name: str, input: UpdateVesselInput):
    try:
        result = CtdService.update_vessel(vessel_name, input)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.delete('/vessels/delete/{vessel_name}', tags=["Admin"], auth=TokenAuthenticator())
def delete_vessel(request, vessel_name: str):
    try:
        result = CtdService.delete_vessel(vessel_name)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.get("/vessels/{vessel_name}", response=VesselOutput, tags=["Users"])
def get_vessel(request, vessel_name: str):
    return CtdService.get_vessel(vessel_name)


@router.get("/cruises/all", response=List[CruiseOutput], tags=["Users"])
def get_cruises(request):
    return CtdService.get_cruises()

@router.get("/cruises/readme", response=str, tags=["Users"])
def get_cruise_readme_all(request):
    return CtdService.get_cruise_readme_all()
        
@router.post('/cruises/create', tags=["Admin"], auth=TokenAuthenticator())
def create_cruise(request, input: AddCruiseInput):
    try:
        new_cruise = CtdService.create_cruise(input)
        return {"status": "success", "cruise": new_cruise}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.post('/cruises/update/{cruise_name}', tags=["Admin"], auth=TokenAuthenticator())
def update_cruise(request, cruise_name: str, input: UpdateCruiseInput):
    try:
        result = CtdService.update_cruise(cruise_name, input)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@router.delete('/cruises/delete/{cruise_name}', tags=["Admin"], auth=TokenAuthenticator())
def delete_cruise(request, cruise_name: str):
    try:
        result = CtdService.delete_cruise(cruise_name)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.get("/cruises/{cruise_name}", response=CruiseOutput, tags=["Users"])
def get_cruise(request, cruise_name: str):
    return CtdService.get_cruise(cruise_name)

@router.get("/cruises/readme/{cruise_name}", response=str, tags=["Users"])
def get_cruise_readme(request, cruise_name: str):
    return CtdService.get_cruise_readme(cruise_name)


@router.post('/casts/create', tags=["Admin"], auth=TokenAuthenticator())
def create_cast(request, input: CastInput):
    try:
        new_cast = CtdService.create_cast(input)
        return {"status": "success", "cast": new_cast}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    
@router.post('/casts/update/{cruise_name}/{cast_number}', tags=["Admin"], auth=TokenAuthenticator())
def update_cast(request, cruise_name: str, cast_number: str, input: UpdateCastInput):
    try:
        cast = CtdService.update_cast(cruise_name, cast_number, input)
        return {"status": "success", "cast updated": cast}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.delete('/casts/delete/{cruise_name}/{cast_number}', tags=["Admin"], auth=TokenAuthenticator())
def delete_cast(request, cruise_name: str, cast_number: str):
    try:
        result = CtdService.delete_cast(cruise_name, cast_number)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.get("/casts/{cruise_name}", response=List[CastOutput], tags=["Users"])
def get_casts(request, cruise_name: str):
    return CtdService.get_casts(cruise_name)
  
@router.get("/cast/{cruise_name}/{cast_number}", tags=["Users"])
def get_cast(request, cruise_name: str, cast_number: str):
    return CtdService.get_cast(cruise_name, cast_number)

    
@router.post('/niskins/create', tags=["Admin"], auth=TokenAuthenticator())
def create_niskin(request, input: NiskinInput):
    try:
        niskin = CtdService.create_niskin(input)
        return {"status": "success", "niskin": niskin}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    
@router.get("/niskins/all/{cruise_name}/{cast_number}", response=List[NiskinOutput], tags=["Users"])
def get_niskins(request, cruise_name: str, cast_number: str):
    return CtdService.get_niskins(cruise_name, cast_number)

@router.get("/niskins/{cruise_name}/{cast_number}/{niskin_number}", response=NiskinOutput, tags=["Users"])
def get_niskin(request, cruise_name: str, cast_number: str, niskin_number: int):
    return CtdService.get_niskin(cruise_name, cast_number, niskin_number)

@router.post('/niskins/update/{cruise_name}/{cast_number}/{niskin_number}', tags=["Admin"], auth=TokenAuthenticator())
def update_niskin(request, cruise_name: str, cast_number: str, niskin_number: str, input: UpdateNiskinInput):
    try:
        niskin = CtdService.update_niskin(cruise_name, cast_number, niskin_number, input)
        return {"status": "success", "niskin updated": niskin}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.delete('/niskins/delete/{cruise_name}/{cast_number}/{niskin_number}', tags=["Admin"], auth=TokenAuthenticator())
def delete_niskin(request, cruise_name: str, cast_number: str, niskin_number: int):
    try:
        result = CtdService.delete_niskin(cruise_name, cast_number, niskin_number)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@router.get("/bottles/{cruise_name}", tags=["Users"])
def get_bottles(request, cruise_name: str):
    return CtdService.get_bottles(cruise_name)

@router.get("/bottle_summary/{cruise_name}", tags=["Users"])
def get_bottle_summary(request, cruise_name: str):
    return CtdService.get_bottle_summary(cruise_name)

@router.get("/metadata/{cruise_name}", tags=["Users"])
def get_metadata(request, cruise_name: str):
    return CtdService.get_metadata(cruise_name)

@router.get("/bathymetry_file", tags=["Users"])
def get_bathymetry(request):
    return CtdService.get_bathymetry()

