from django.urls import path

from home.health_views import liveness, readiness

urlpatterns = [
    path("live", liveness, name="health-live"),
    path("ready", readiness, name="health-ready"),
]
