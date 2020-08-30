from django.urls import path
from . import views

app_name = 'app_upload_DRF_avail_report'

urlpatterns =[
path('DRF_avail_report/', views.DRF_Report,name='DRF_Report'),

]
