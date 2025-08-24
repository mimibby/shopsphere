from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegisterForm

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully!")

            # ✅ Send confirmation email
            subject = "Welcome to ShopSphere!"
            message = f"Hi {user.username},\n\nThank you for registering at ShopSphere. Your account has been created successfully.\n\nHappy shopping!\n\n– The StyleVerse Team"
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            return redirect('accounts:login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:home')  

    if request.method == 'POST':
        username = request.POST.get('username')  
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('shop:home')  
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'accounts/login.html')  


def logout_view(request):
    logout(request)
    return redirect('accounts:login')