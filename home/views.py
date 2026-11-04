from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from home.models import Conversation


def home(request):
    conversation = None
    if request.user.is_authenticated:
        conversation = Conversation.objects.filter(owner=request.user).order_by("-last_accessed_at").first()
    return render(request, "home/index.html", {"conversation": conversation})


@login_required
@require_POST
def start_conversation(request):
    Conversation.objects.create(owner=request.user)
    return redirect("home")
