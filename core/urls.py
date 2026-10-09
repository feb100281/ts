from django.urls import path
from .views import run_gl_etl

urlpatterns = [
    path("run-gl-etl/", run_gl_etl, name="run_gl_etl"),
]