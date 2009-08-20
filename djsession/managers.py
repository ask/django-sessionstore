from django.db import models


class TableversionManager(models.Manager):

    def _get_current_table(self, table):
        tv, created = self.get_or_create(table=table)
        return tv

    def _get_previous_table(self, table):
        cv = self._get_current_table(table)
        version = cv.version - 1 if cv.version else 0
        pv = self.model(table=table, version=version)
        pv.save = None # Disable save
        return pv

    def get_current_table_name(self, table):
        return self._get_current_table(table).db_table

    def get_previous_table_name(self, table):
        return self._get_previous_table(table).db_table
