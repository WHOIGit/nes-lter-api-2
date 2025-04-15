from django.urls import path
from ninja import NinjaAPI
from rest_framework.authtoken.views import obtain_auth_token

from core.api import router as core_router
from stations.api import router as stations_router
from ctd.api import router as ctd_router
from events.api import router as events_router
from underway.api import router as underway_router
from hplc.api import router as hplc_router
from nut.api import router as nut_router
from chl.api import router as chl_router

from .views import file_upload_view, cruise_track_view, ctd_plot_view

api = NinjaAPI()

api.add_router('', core_router)
api.add_router('/stations/', stations_router)
api.add_router('/ctd/', ctd_router)
api.add_router('/events/', events_router)
api.add_router('/underway/', underway_router)
api.add_router('/hplc/', hplc_router)
api.add_router('/nut/', nut_router)
api.add_router('/chl/', chl_router)

urlpatterns = [
    path('api/login', obtain_auth_token), # a bit of a hack to use the DRF obtain_auth_token view
    path('api/', api.urls),
    path('upload/', file_upload_view, name='file-upload'),
    path('cruise/<str:cruise_name>/track/', cruise_track_view, name='cruise_track'),
    path('cruise/<str:cruise_name>/cast/<str:cast_number>/ctd_plot/', ctd_plot_view, name='ctd_plot'),
]
