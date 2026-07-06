from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def landing_home(request):
    return render(request, 'landing/index.html')


def landing_about(request):
    return render(request, 'landing/about.html')


def landing_contact(request):
    return render(request, 'landing/contact.html')


def landing_benefits(request):
    return render(request, 'landing/beneficios.html')


def landing_functionalities(request):
    return render(request, 'landing/funcionalidades.html')


def landing_faq(request):
    return render(request, 'landing/products.html')


def legacy_landing_redirect(request, page):
    rutas = {
        'index': '/',
        'about': '/nosotros/',
        'contact': '/contacto/',
        'products': '/products.html',
        'courses': '/beneficios/',
        'instructors': '/funcionalidades/',
        'beneficios': '/beneficios/',
        'funcionalidades': '/funcionalidades/',
    }

    return redirect(rutas.get(page, '/'))


@login_required
def dashboard(request):
    return render(request, 'base.html')