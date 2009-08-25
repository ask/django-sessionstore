from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.sessions.models import Session
from djsession.managers import TableversionManager
from django.db.models import signals
from django.core.management.color import no_style
from django.db import connection

PREVIOUS_TABLE_NAME="django_session_0"
CURRENT_TABLE_NAME="django_session_1"

def table_created(model):
    tables = connection.introspection.table_names()
    abs_name = connection.introspection.table_name_converter(
            model._meta.db_table)
    if abs_name in tables:
        return True
    return False


class Tableversion(models.Model):
    table = models.CharField(_(u"table"), max_length=255, unique=True)
    version = models.IntegerField(_(u"version"), default=1)

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
        db_table = PREVIOUS_TABLE_NAME

    def __init__(self, *args, **kwargs):
        super(PrevSession, self).__init__(*args, **kwargs)
        self.__class__._meta.db_table = PREVIOUS_TABLE_NAME

PrevSession._meta.db_table = PREVIOUS_TABLE_NAME


class CurrentSession(Session):
    
    class Meta:
        proxy = True
        db_table = CURRENT_TABLE_NAME

    def __init__(self, *args, **kwargs):
        super(CurrentSession, self).__init__(*args, **kwargs)
        self.__class__._meta.db_table = CURRENT_TABLE_NAME

CurrentSession._meta.db_table = CURRENT_TABLE_NAME


def force_create_table(model, verbosity=0):
    """Force creation of proxy table.

    **NOTE** Does not create references.

    """
    if table_created(model):
        return False
    old_proxy = model._meta.proxy
    old_local_fields = model._meta.local_fields
    model._meta.proxy = False
    model._meta.local_fields = model._meta.local_fields + model._meta.fields
    sql, references = connection.creation.sql_create_model(model, no_style())
    model._meta.proxy = old_proxy
    model._meta.local_fields = old_local_fields
    cursor = connection.cursor()
    map(cursor.execute, sql)
    if verbosity >= 1 and sql:
        print("Creating table: %s" % model._meta.db_table)
    return True

def on_post_syncdb(app, created_models, verbosity=2, **kwargs):
    if app.__name__ != __name__:
        return
    # Tableversions table is now created.
    PrevSession._meta.db_table = PREVIOUS_TABLE_NAME
    CurrentSession._meta.db_table = CURRENT_TABLE_NAME
    force_create_table(PrevSession, verbosity=verbosity)
    force_create_table(CurrentSession, verbosity=verbosity)
signals.post_syncdb.connect(on_post_syncdb)

