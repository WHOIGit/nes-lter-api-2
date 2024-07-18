from django.urls import path
from ninja import NinjaAPI
from rest_framework.authtoken.views import obtain_auth_token

from core.api import router as core_router
from stations.api import router as stations_router

api = NinjaAPI()

api.add_router('', core_router)
api.add_router('/stations/', stations_router)

urlpatterns = [
    path('api/login', obtain_auth_token), # a bit of a hack to use the DRF obtain_auth_token view
    path('api/', api.urls),
]
