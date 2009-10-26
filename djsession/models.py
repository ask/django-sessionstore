from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import SessionManager
from djsession.managers import TableversionManager
from django.db.models import signals
from django.core.management.color import no_style
from django.db import connection

class Tableversion(models.Model):
    """
    This model is used to keep the state of the table rotation revisions.
    The greatest current_version is the official used table.
    """
    current_version = models.IntegerField(_(u"version"), default=1)
    latest_rotation = models.DateTimeField(_(u"latest rotation"),
        auto_now_add=True)

    objects = TableversionManager()
    
    class Meta:
        get_latest_by = ('current_version')
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

def get_session_table_name():
    if version_table_created():
        try:
            # try to get the latest version number
            current_version = Tableversion.objects.latest().current_version
        except Tableversion.DoesNotExist:
            current_version = 1
    else:
        current_version = 1
    previous_version = int(current_version -1)

    # boot up the table name with the default table name for the sessions
    # this will facilite a migration from the old session backend to this one.
    if previous_version == 0:
        previous_table_name="django_session"
    else:
        previous_table_name="django_session_%d" % int(current_version -1)
    current_table_name="django_session_%d" % current_version
    return previous_table_name, current_table_name

# set up session table name
PREVIOUS_TABLE_NAME, CURRENT_TABLE_NAME = get_session_table_name()

class Session(models.Model):
    """Replication of the session Model."""
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

