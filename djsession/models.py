from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import Session
from djsession.managers import TableversionManager


class Tableversion(models.Model):
    table = models.CharField(_(u"table"), max_length=255, unique=True)
    version = models.IntegerField(_(u"version"), default=0)

    objects = TableversionManager()

    class Meta:
        verbose_name = _("table version")
        verbose_name_plural = _(u"table versions")

    def __unicode__(self):
        return self.db_table

    @property
    def db_table(self):
        version = "_v" + str(self.version) if self.version > 0 else str()
        return "%s%s" % (self.table, version)


class PrevSession(Session):

    class Meta:
        proxy = True
PrevSession._meta.db_table = Tableversion.objects.get_previous_table_name(
        PrevSession._meta.db_table)


class CurrentSession(Session):

    class Meta:
        proxy = True
CurrentSession._meta.db_table = Tableversion.objects.get_current_table_name(
        CurrentSession._meta.db_table)
