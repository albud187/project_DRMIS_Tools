"""project_DRMIS_Tools URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from . import views

MM_tools_list =[
path('app_upload_test', include('app_upload_test.urls',namespace='app_upload_test')),
path('app_DRF_avail_report', include('app_DRF_avail_report.urls',namespace='app_DRF_avail_report'))

]

FI_tools_list =[

]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.HomePage.as_view(),name='home'),
    path('about',views.AboutPage.as_view(),name='about'),
    path('MM_tools/',views.MMToolsView.as_view(),name='MM_Tools'),
    path('FI_tools/',views.FIToolsView.as_view(),name='FI_Tools'),
] + MM_tools_list + FI_tools_list
