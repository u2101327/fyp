from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
# from .documents import CredentialLeakDocument, MonitoredCredentialDocument  # Disabled - requires OpenSearch

from .models import *
from .forms import CreateUserForm, MonitoredCredentialForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def registerPage(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account was created for {user.username}! You can now log in.")
            return redirect('login')
    else:
        form = CreateUserForm()

    return render(request, 'register.html', {"form": form})


def loginPage(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')

    context = {}
    return render(request, 'login.html', context)

@login_required
def dashboard(request):

    rows = []
    for mc in MonitoredCredential.objects.filter(owner=request.user):
        if mc.email:
            rows.append({"cred_type": "email", "value": mc.email})
        if mc.username:
            rows.append({"cred_type": "username", "value": mc.username})
        if mc.domain:
            rows.append({"cred_type": "domain", "value": mc.domain})

    return render(request, 'dashboard.html', {"monitored_credentials": rows})


@login_required
@require_POST
def add_monitored_credential(request):

    cred_type = (request.POST.get("cred_type") or "").strip()
    value = (request.POST.get("value") or "").strip()

    if not cred_type or not value:
        messages.error(request, "Please choose a type and enter a value.")
        return redirect('dashboard')
    
    try:
        if cred_type == "email":
            obj, created = MonitoredCredential.objects.get_or_create(
                owner=request.user, email=value
            )
        elif cred_type == "username":
            obj, created = MonitoredCredential.objects.get_or_create(
                owner=request.user, username=value
            )
        elif cred_type == "domain":
            obj, created = MonitoredCredential.objects.get_or_create(
                owner=request.user, domain=value.lower()
            )
        else:
            messages.error(request, "Unknown credential type.")
            return redirect("dashboard")
    except Exception:
        messages.error(request, "Could not save credential.")
        return redirect("dashboard")

    if created:
        messages.success(request, "Credential added and will be monitored.")
    else:
        messages.info(request, "That credential is already being monitored.")
    return redirect("dashboard")

@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')   
