"""Session backend that first tries the cache, then tries the tablerotated
database backend."""
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from djsession.backends.db import SessionStore as DBStore
from django.core.cache import cache


class SessionStore(DBStore):

    def load(self):
        session_data = cache.get(self.session_key, None)
        if session_data is None:
            session_data = super(SessionStore, self).load()
            cache.set(self.session_key, session_data,
                      settings.SESSION_COOKIE_AGE)

    def save(self, must_create=False):
        super(SessionStore, self).save(must_create)
        cache.set(self.session_key, self._session,
                  settings.SESSION_COOKIE_AGE)
    
    def delete(self, session_key=None):
        super(SessionStore, self).delete(session_key)
        cache.delete(session_key or self.session_key)

    def flush(self):
        """Removes the current session data from the database and
        regenerates the key."""
        self.clear()
        self.delete(self.session_key)
        self.create()
