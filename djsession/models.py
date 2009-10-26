from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import SessionManager
from djsession.managers import TableversionManager
from django.db.models import signals
from django.core.management.color import no_style

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

# set up session table name
PREVIOUS_TABLE_NAME, CURRENT_TABLE_NAME = Tableversion.objects.get_session_table_name()

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

