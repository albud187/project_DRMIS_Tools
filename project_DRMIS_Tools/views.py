from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

class HomePage(TemplateView):
    template_name = 'home.html'

class AboutPage(TemplateView):
    template_name = 'about.html'

class MMToolsView(TemplateView):
    template_name = 'tools_MM.html'

class  FIToolsView(TemplateView):
    template_name = 'tools_FI.html'
