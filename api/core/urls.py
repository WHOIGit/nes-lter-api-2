from django.urls import path
from ninja import NinjaAPI
from core.api import router as core_router
from stations.api import router as stations_router

api = NinjaAPI()

api.add_router('', core_router)
api.add_router('/stations/', stations_router)

urlpatterns = [
    path('api/', api.urls),
]
