# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Club'
        db.create_table(u'site_club', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=400)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal(u'site', ['Club'])

        # Adding model 'RaceCourse'
        db.create_table(u'site_racecourse', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('location', self.gf('geoposition.fields.GeopositionField')(max_length=42)),
        ))
        db.send_create_signal(u'site', ['RaceCourse'])

        # Adding model 'RacePrototype'
        db.create_table(u'site_raceprototype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('time', self.gf('django.db.models.fields.TimeField')()),
            ('club', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['site.Club'])),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['site.RaceCourse'])),
        ))
        db.send_create_signal(u'site', ['RacePrototype'])

        # Adding model 'Race'
        db.create_table(u'site_race', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('time', self.gf('django.db.models.fields.TimeField')()),
            ('club', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['site.Club'])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=400, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['site.RaceCourse'])),
        ))
        db.send_create_signal(u'site', ['Race'])


    def backwards(self, orm):
        # Deleting model 'Club'
        db.delete_table(u'site_club')

        # Deleting model 'RaceCourse'
        db.delete_table(u'site_racecourse')

        # Deleting model 'RacePrototype'
        db.delete_table(u'site_raceprototype')

        # Deleting model 'Race'
        db.delete_table(u'site_race')


    models = {
        u'site.club': {
            'Meta': {'ordering': "['name']", 'object_name': 'Club'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        u'site.race': {
            'Meta': {'ordering': "['date', 'time']", 'object_name': 'Race'},
            'club': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['site.Club']"}),
            'date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['site.RaceCourse']"}),
            'time': ('django.db.models.fields.TimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '400', 'blank': 'True'})
        },
        u'site.racecourse': {
            'Meta': {'object_name': 'RaceCourse'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('geoposition.fields.GeopositionField', [], {'max_length': '42'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'site.raceprototype': {
            'Meta': {'object_name': 'RacePrototype'},
            'club': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['site.Club']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['site.RaceCourse']"}),
            'time': ('django.db.models.fields.TimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['site']