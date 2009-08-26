# -*- coding: utf-8 -*-
"""Django session table rotation tests."""
import django
import re
from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django import db
from djsession.backends.db import SessionStore
from djsession.models import CurrentSession, PrevSession

class DJsessionTestCase(TestCase):

    def test_01_simple(self):
        """Basic tests."""
        settings.DEBUG = True
        session = SessionStore()
        self.assertFalse(session.exists('0360e53e4a8e381de3389b11455facd7'))
        django1 = db.connection.queries[0]
        self.assertTrue('django_session_1' in django1['sql'])
        django0 = db.connection.queries[1]
        self.assertTrue('django_session_0' in django0['sql'])
        db.reset_queries()
        
        session['toto'] = 'toto'
        session.save()
        db.reset_queries()
        
        session_key = session.session_key
        session = SessionStore(session_key=session_key)
        self.assertEqual(session['toto'], 'toto')
        self.assertEqual(len(db.connection.queries), 1)

        session.delete()

        session = SessionStore(session_key=session_key)
        self.assertFalse('toto' in session)
        
        settings.DEBUG = False

    def test_02_session_migration(self):
        """Test that a session is migrated from an old table
        to the current table properly."""

        settings.DEBUG = True
        from django import db

        # save a session in the previous table
        session = SessionStore(
            previous=CurrentSession,
            current=PrevSession
        )
        session['tata'] = 'tata'
        session.save()
        session_key = session.session_key

        db.reset_queries()
        session = SessionStore(session_key=session_key)
        self.assertEqual(session['tata'], 'tata')
        self.assertEqual(len(db.connection.queries), 4)

        # this time, because the session is in the last table,
        # we have only one request
        db.reset_queries()
        session = SessionStore(session_key=session_key)
        self.assertEqual(session['tata'], 'tata')
        self.assertEqual(len(db.connection.queries), 1)
        
        
        settings.DEBUG = False
