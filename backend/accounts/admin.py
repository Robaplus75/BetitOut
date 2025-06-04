from django.contrib import admin
from .models import CustomUserManager, User, Wallet

# Register your models here.

admin.site.register(User)
admin.site.register(Wallet)
