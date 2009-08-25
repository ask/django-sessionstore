from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import SessionManager
from djsession.managers import TableversionManager
from django.db.models import signals
from django.core.management.color import no_style
from django.db import connection

class Tableversion(models.Model):
    current_version = models.IntegerField(_(u"version"), default=1)

    class Meta:
        verbose_name = _("table version")
        verbose_name_plural = _(u"table versions")

    def __unicode__(self):
        return "django_session_%d" % self.current_version

def version_table_created():
    """Tell if the TableVersion is available or need to be created"""
    tables = connection.introspection.table_names()
    abs_name = connection.introspection.table_name_converter(
            Tableversion._meta.db_table)
    if abs_name in tables:
        return True
    return False

if version_table_created():
    try:
        # try to get the latest version number
        current_version = Tableversion.objects.order_by('-current_version')[0]
    except IndexError:
        current_version = 1
else:
    current_version = 1

PREVIOUS_TABLE_NAME="django_session_%d" % int(current_version -1)
CURRENT_TABLE_NAME="django_session_%d" % current_version

class Session(models.Model):
    """Replication of the session Model"""
    session_key = models.CharField(_('session key'), max_length=40,
                                   primary_key=True)
    session_data = models.TextField(_('session data'))
    expire_date = models.DateTimeField(_('expire date'))
    # we inherit the session manager... No sure it's
    # a good idea to rely on this code.
    objects = SessionManager()

    class Meta:
        abstract = True

class PrevSession(Session):

    class Meta:
        db_table = PREVIOUS_TABLE_NAME

class CurrentSession(Session):
    
    class Meta:
        db_table = CURRENT_TABLE_NAME

