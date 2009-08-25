from datetime import datetime
from djsession.models import CurrentSession, PrevSession
from django.contrib.sessions.backends.base import CreateError
from django.contrib.sessions.backends.db import SessionStore as DBStore

from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction
from django.utils.encoding import force_unicode


class SessionStore(DBStore):
    """Get/save sessions from the database."""

    model = CurrentSession

    def __init__(self, session_key=None, model=None, create_if_missing=True):
        #self.model = model or self.model
        self.DoesNotExist = self.model.DoesNotExist
        self.create_if_missing = create_if_missing
        super(SessionStore, self).__init__(session_key=session_key)

    def load(self):
        try:
            s = self.model.objects.get(session_key=self.session_key)
            return self.decode(force_unicode(s.session_data))
        except (self.DoesNotExist, SuspiciousOperation):
            if self.create_if_missing:
                self.create()
            return {}

    def create(self):
        while True:
            self.session_key = self._get_new_session_key()
            try:
                # Save immediately to ensure we have a unique entry in the
                # database.
                self.save(must_create=True)
            except CreateError:
                # Key wasn't unique. Try again.
                continue
            self.modified = True
            self._session_cache = {}
            return

    def exists(self, session_key):
        try:
            self.model.objects.get(session_key=session_key)
        except self.model.DoesNotExist:
            return False
        return True

    """def get(self, session_key, **lookup):
        lookup = lookup or {}
        lookup["session_key"] = session_key
        return self.model.objects.get(**lookup)"""

    def exists(self, session_key):
        try:
            s = self.model.objects.get(session_key = self.session_key)
        except self.DoesNotExist:
            return False
        return True

    """def create(self):"""

    def save(self, must_create=False):
        session_data = self._get_session(no_load=must_create)
        self._save(session_data, must_create=must_create)

    def init_from_other(self, other, must_create=False):
        session_data = other._get_session(no_load=False)
        return self._save(session_data, must_create=must_create)

    def _save(self, session_data, must_create=False):
        session_data = self.encode(session_data)
        obj = self.model(session_key=self.session_key,
                         session_data=session_data,
                         expire_date=self.get_expiry_date())
        sid = transaction.savepoint()
        try:
            print "SAVE OBJECT"
            obj.save(force_insert=must_create)
            from django.db import connection
            print connection.queries
        except IntegrityError:
            if must_create:
                transaction.savepoint_rollback(sid)
                raise CreateError
            raise

    def delete(self, session_key=None):
        if session_key is None:
            if self._session_key is None:
                return
            session_key = self._session_key
        try:
            self.model.objects.get(session_key=self.session_key).delete()
        except self.DoesNotExist:
            pass

