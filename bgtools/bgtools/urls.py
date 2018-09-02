"""bgtools URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static

from dominion_dividers import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^preview/$', views.preview, name='preview'),
    url(r'^chitboxes/$', views.chitboxes, name='chitboxes'),
    url(r'^tuckboxes/$', views.tuckboxes, name='tuckboxes'),
    url(r'^domdiv/$', views.index, name='domdiv')
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
