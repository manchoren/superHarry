import uuid

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from home.file_store import FileStoreError, detect_content_type, open_download_stream, upload


def _request_id(request):
    request_id = getattr(request, "file_request_id", None)
    if request_id is None:
        request_id = uuid.uuid4()
        request.file_request_id = request_id
    return request_id


def _response(response):
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def upload_file(request):
    request_id = _request_id(request)
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return _response(JsonResponse({"error": "FILE_REQUIRED", "request_id": str(request_id)}, status=400))
    try:
        record = upload(user=request.user, uploaded_file=uploaded, request_id=request_id)
    except (FileStoreError, OSError, ValueError):
        return _response(JsonResponse({"error": "FILE_REJECTED", "request_id": str(request_id)}, status=413))
    return _response(JsonResponse(
        {"id": str(record.storage_id), "size": record.size, "request_id": str(request_id)}, status=201
    ))


@login_required
@require_GET
def download_file(request, storage_id: uuid.UUID):
    request_id = _request_id(request)
    try:
        record, stream = open_download_stream(user=request.user, storage_id=storage_id, request_id=request_id)
    except (FileStoreError, OSError, ValueError):
        return _response(JsonResponse({"error": "FILE_UNAVAILABLE", "request_id": str(request_id)}, status=404))
    content_type = detect_content_type(stream.read(16))
    stream.seek(0)
    response = FileResponse(stream, as_attachment=True, filename=record.original_name,
                            content_type=content_type)
    response["X-Request-ID"] = str(request_id)
    return _response(response)
