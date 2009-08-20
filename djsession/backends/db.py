from datetime import datetime
from djsession.models import CurrentSession, PrevSession
from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction
from django.utils.encoding import force_unicode


class SessionDB(SessionBase):
    """Get/save sessions from the database."""

    model = CurrentSession

    def __init__(self, session_key=None, model=None, create_if_missing=True):
        self.model = model or self.model
        self.DoesNotExist = self.model.DoesNotExist
        self.create_if_missing = create_if_missing
        super(SessionDB, self).__init__(session_key=session_key)

    def load(self):
        now = datetime.now()
        try:
            s = self.get(self.session_key, expire_date__gt=now)
        except (self.DoesNotExist, SuspiciousOperation):
            if self.create_if_missing:
                self.create()
            return {}

    def get(self, session_key, **lookup):
        lookup = lookup or {}
        lookup["session_key"] = session_key
        return self.model.objects.get(**lookup)

    def exists(self, session_key):
        try:
            self.get(session_key)
        except self.DoesNotExist:
            return False
        return True

    def create(self):
        while True:
            self.session_key = self._get_new_session_key()
            try:
                # Save immediately to ensure we have a unique entry
                # in the database
                self.save(must_create=True)
            except CreateError:
                # Key wasn't unique. Try again.
                continue
            self.modified = True
            self._session_cache = {}
            return

    def save(self, must_create=False):
        session_data = self._get_session(no_load=must_create)
        return self._save(session_data, must_create=must_create)

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
            self.get(session_key).delete()
        except self.DoesNotExist:
            pass


class SessionStore(SessionBase):

    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key=session_key)
        self.current = SessionDB(self.session_key, model=CurrentSession)
        self.previous = SessionDB(self.session_key, model=PrevSession,
                                  create_if_missing=False)

    def _sync_with_other_session(self, session):
        self.session_key = other.session_key
        self.modified = other.modified
        self.accessed = other.accessed

        # Sync with the other session cache (if any
        if hasattr(other, "_session_cache"):
            self._session_cache = other._session_cache
        else:
            try:
                delattr(self, "_session_cache")
            except AttributeError:
                pass

    def load(self):
        current_session = self.current.load()
        if not current_session:
            prev_session = self.previous.load()
            if prev_session:
                self.current.init_with_other(prev_session, must_create=True)
            self._sync_with_other_session(self.current)
            return prev_session
        self._sync_with_other_session(self.current)
        return current_session

    def save(self):
        s = self.current.save()
        self._sync_with_other_session(self.current)

    def exists(self, session_key):
        return self.current.exists(session_key) or \
                    self.previous.exists(session_key)

    def create(self):
        s = self.current.create()
        self._sync_with_other_session(self.current)

    def delete(self):
        self.previous.delete()
        self.current.delete()
        self._sync_with_other_session(self.current)
