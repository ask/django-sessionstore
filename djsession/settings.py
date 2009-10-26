"""Django session settings"""
from django.conf import settings

DJSESSION_EXPIRE_DAYS = getattr(settings,
       "DJSESSION_EXPIRE_DAYS", 3)