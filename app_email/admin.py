from django.contrib import admin
from app_email.models import *
# Register your models here.https://www.snapdeal.com/product/lenovo-ideapad-ideapad-110-notebook/661530013122
class EmailInfoAdmin(admin.ModelAdmin):
	filter_horizontal=('products','to_group')


admin.site.register(EmailInfo,EmailInfoAdmin)
admin.site.register(Website)
admin.site.register(Product)