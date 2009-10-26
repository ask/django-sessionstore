# -*- coding: utf-8 -*-
"""Django session table rotation tests."""
import django
import re
import datetime
from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django import db
from django.db import connection, transaction
from djsession.backends.db import SessionStore
from djsession.models import CurrentSession, PrevSession
from djsession.models import Tableversion
from djsession.settings import DJSESSION_EXPIRE_DAYS

class DJsessionTestCase(TestCase):

    def test_01_simple(self):
        """Basic tests."""
        settings.DEBUG = True
        session = SessionStore()
        self.assertFalse(session.exists('0360e53e4a8e381de3389b11455facd7'))
        django1 = db.connection.queries[0]
        self.assertTrue('django_session_1' in django1['sql'])
        django0 = db.connection.queries[1]
        self.assertTrue('django_session' in django0['sql'])
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

    def test_03_table_name(self):
        """Test that the table name is properly set up."""

        self.assertEqual(Tableversion.objects.get_session_table_name(),
            ('django_session', 'django_session_1'))

        Tableversion(current_version=2).save()

        self.assertEqual(Tableversion.objects.get_session_table_name(),
            ('django_session_1', 'django_session_2'))

        Tableversion(current_version=3).save()

        self.assertEqual(Tableversion.objects.get_session_table_name(),
            ('django_session_2', 'django_session_3'))
        
        settings.DEBUG = False


    def test_04_rotate_table(self):
        """Test that the rotation functions works."""
        self.assertEqual(Tableversion.objects.get_session_table_name(),
            ('django_session', 'django_session_1'))

        self.assertEqual(Tableversion.objects.rotate_table().current_version, 1)
        self.assertEqual(Tableversion.objects.rotate_table().current_version, 1)

        self.assertTrue("django_session_1" in connection.introspection.table_names())
        self.assertFalse("django_session_2" in connection.introspection.table_names())

        self.assertEqual(Tableversion.objects.get_session_table_name(),
            ('django_session', 'django_session_1'))

        delta = datetime.timedelta(days=DJSESSION_EXPIRE_DAYS + 1)

        lastest = Tableversion.objects.latest()
        lastest.latest_rotation = datetime.datetime.now() - delta
        lastest.save()

        self.assertEqual(Tableversion.objects.rotate_table().current_version, 2)
        self.assertEqual(Tableversion.objects.rotate_table().current_version, 2)

        self.assertEqual(Tableversion.objects.get_session_table_name(),
            ('django_session_1', 'django_session_2'))

        self.assertTrue("django_session_2" in connection.introspection.table_names())

        self.assertTrue("django_session" in connection.introspection.table_names())
        Tableversion.objects.cleanup_old_session_table()
        self.assertTrue("django_session" not in connection.introspection.table_names())

        cursor = connection.cursor()
        sql = """
        SELECT * FROM "django_session_2";
        """
        cursor.execute(sql)
        transaction.commit_unless_managed()
        try:
            cursor.next()
        except StopIteration:
            pass
