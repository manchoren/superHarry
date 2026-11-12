import uuid

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from home.file_store import FileStoreError, open_for_download, upload


@login_required
@require_POST
def upload_file(request):
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"error": "FILE_REQUIRED"}, status=400)
    try:
        record = upload(user=request.user, uploaded_file=uploaded)
    except (FileStoreError, OSError, ValueError):
        return JsonResponse({"error": "FILE_REJECTED"}, status=413)
    return JsonResponse({"id": str(record.storage_id), "size": record.size}, status=201)


@login_required
@require_GET
def download_file(request, storage_id: uuid.UUID):
    try:
        record, path = open_for_download(user=request.user, storage_id=storage_id)
    except (FileStoreError, OSError, ValueError):
        return JsonResponse({"error": "FILE_UNAVAILABLE"}, status=404)
    return FileResponse(path.open("rb"), as_attachment=True, filename=record.original_name,
                        content_type=record.content_type or "application/octet-stream")
