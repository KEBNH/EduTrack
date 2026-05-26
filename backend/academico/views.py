from django.shortcuts import render


def portada(request):
    return render(request, 'landing/portada.html')


def inicio(request):
    return render(request, 'academico/base.html')


def estudiante(request):
    return render(request, 'academico/estudiante.html')
