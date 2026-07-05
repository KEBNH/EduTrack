from django.shortcuts import render


def landing(request):
    return render(request, "landing/index.html")


def landing_about(request):
    return render(request, "landing/about.html")


def landing_contact(request):
    return render(request, "landing/contact.html")


def landing_benefits(request):
    return render(request, "landing/beneficios.html")


def landing_functionalities(request):
    return render(request, "landing/funcionalidades.html")
