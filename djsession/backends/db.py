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
        self.model = model or self.model
        self.DoesNotExist = self.model.DoesNotExist
        self.create_if_missing = create_if_missing
        super(SessionStore, self).__init__(session_key=session_key)

    def load(self):
        try:
            print self.model
            s = self.model.objects.get(session_key=self.session_key)
            return self.decode(force_unicode(s.session_data))
        except (self.DoesNotExist, SuspiciousOperation):
            if self.create_if_missing:
                self.create()
            return {}

    def exists(self, session_key):
        try:
            self.model.objects.get(session_key=session_key)
        except self.model.DoesNotExist:
            return False
        return True

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
            obj.save(force_insert=must_create)
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

