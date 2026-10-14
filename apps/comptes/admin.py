from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "role", "centre", "is_active")
    list_filter = ("role", "centre", "is_active", "is_staff", "groups")
    fieldsets = UserAdmin.fieldsets + (
        ("UNIPOD", {"fields": ("role", "centre", "telephone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("UNIPOD", {"fields": ("first_name", "last_name", "email", "role", "centre")}),
    )
