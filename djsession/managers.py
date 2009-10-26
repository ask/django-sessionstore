from django.db import models
import datetime
from django.conf import settings
from djsession.settings import DJSESSION_EXPIRE_DAYS

class TableversionManager(models.Manager):

    def rotate_table(self):
        """Rotate the session table, create session tables if necessary."""
        from djsession.models import Tableversion, get_session_table_name
        try:
            latest_version = self.latest()
        except Tableversion.DoesNotExist:
            table_1, table_2 =  get_session_table_name()
            self.create_session_table(table_1)
            self.create_session_table(table_2)
            latest_version = Tableversion(current_version=1)
            latest_version.save()
            return latest_version
        now = datetime.datetime.now()
        delta = now - latest_version.latest_rotation
        min_delta = datetime.timedelta(days=DJSESSION_EXPIRE_DAYS)
        if min_delta > delta:
            return latest_version
        incresead_version = latest_version.current_version + 1
        latest_version = Tableversion(current_version=incresead_version)
        latest_version.save()
        table_1, table_2 =  get_session_table_name()
        self.create_session_table(table_1)
        self.create_session_table(table_2)
        return latest_version

    def create_session_table(self, table_name="django_session"):
        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = """
        CREATE TABLE IF NOT EXISTS "%s" (
            "session_key" varchar(40) NOT NULL PRIMARY KEY,
            "session_data" text NOT NULL,
            "expire_date" datetime NOT NULL
        );
        """ % table_name
        cursor.execute(sql)
        transaction.commit_unless_managed()
        return "Success"