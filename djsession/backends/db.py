from datetime import datetime, timedelta
from djsession.models import CurrentSession, PrevSession
from django.contrib.sessions.backends.base import CreateError, SessionBase
from django.contrib.sessions.backends.db import SessionStore as DBStore

from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction
from django.utils.encoding import force_unicode
from django.conf import settings


class SessionStore(DBStore):
    """
    This session store is able to work on 2 different session
    tables.

    One is the current session table, the other is an old session table.
    If the session is not found in the current table, the class try on
    the old table. Then the row is created in the current table if
    nothing is found.
    """

    current = CurrentSession
    previous = PrevSession

    def __init__(self, session_key=None, current=None, previous=None):
        self.current = current or self.current
        self.previous = previous or self.previous
        super(SessionStore, self).__init__(session_key=session_key)

    def _get_db_session(self, session_key=None):
        if session_key is None:
            session_key=self.session_key
        try:
            s = self.current.objects.get(session_key=session_key)
            return s
        except (self.current.DoesNotExist, SuspiciousOperation):
            pass
        try:
            s = self.previous.objects.get(session_key=session_key)
            # migrate to the current table
            self._save(self.decode(force_unicode(s.session_data)))
            return s
        except (self.previous.DoesNotExist, SuspiciousOperation):
            return None

    def load(self):
        session = self._get_db_session()
        if session is None:
            self.create()
            return {}
        return self.decode(force_unicode(session.session_data))

    def exists(self, session_key):
        session = self._get_db_session(session_key)
        if session is None:
            return False
        return True

    def save(self, must_create=False):
        session_data = self._get_session(no_load=must_create)
        self._save(session_data, must_create=must_create)

    def _save(self, session_data, must_create=False):
        session_data = self.encode(session_data)
        expire_date = (datetime.utcnow() +
                timedelta(seconds=settings.SESSION_COOKIE_AGE))
        obj = self.current(session_key=self.session_key,
                         session_data=session_data,
                         expire_date=expire_date)
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
            session = self._get_db_session()
            if session is not None:
                session.delete()
