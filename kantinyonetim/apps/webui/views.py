from django.shortcuts import render, redirect


def index(request):
    # front-end token ile auth zorunlu server sadece sayfayi sunar
    return render(request, 'webui/index.html')


def login_view(request):
    # token varsa indexe git yoksa login sayfasini goster
    return render(request, 'webui/login.html')


