from django.urls import path
from . import views

app_name = 'app_upload_test'

urlpatterns =[
path('upload_test/', views.UploadTestView,name='upload_test'),

]
