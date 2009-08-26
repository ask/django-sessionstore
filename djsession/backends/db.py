from datetime import datetime
from djsession.models import CurrentSession, PrevSession
from django.contrib.sessions.backends.base import CreateError, SessionBase
from django.contrib.sessions.backends.db import SessionStore as DBStore

from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction
from django.utils.encoding import force_unicode


class SessionStore(DBStore):
    """Get/save sessions from the database."""

    current = CurrentSession
    previous = PrevSession

    def __init__(self, session_key=None, current=None, previous=None,
                                                    create_if_missing=True):
        self.current = current or self.current
        self.previous = previous or self.previous
        self.DoesNotExist = self.current.DoesNotExist
        self.create_if_missing = create_if_missing
        super(SessionStore, self).__init__(session_key=session_key)

    def _get_db_session(self):
        try:
            s = self.current.objects.get(session_key=self.session_key)
            return s
        except (CurrentSession.DoesNotExist, SuspiciousOperation):
            pass
        try:
            s = self.previous.objects.get(session_key=self.session_key)
            return s
        except (PrevSession.DoesNotExist, SuspiciousOperation):
            return None

    def load(self):
        session = self._get_db_session()
        if session is None:
            if self.create_if_missing:
                self.create()
            return {}
        return self.decode(force_unicode(session.session_data))

    def exists(self, session_key):
        if self._get_db_session() is None:
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
        obj = self.current(session_key=self.session_key,
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
        session = self._get_db_session()
        if session is not None:
            session.delete()
