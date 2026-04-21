from django.contrib import admin
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path


def healthz(_request):
    return JsonResponse({"status": "ok"})


def spa_index(_request, _path=""):
    index_path = settings.FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise Http404("Frontend build not found.")
    return FileResponse(index_path.open("rb"), content_type="text/html")


urlpatterns = [
    path("healthz/", healthz),
    path("admin/", admin.site.urls),
    path("api/", include("budget.urls")),
    re_path(r"^(?!api/|admin/|static/|healthz/).*$", spa_index),
]
