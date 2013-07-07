# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Club.icalurl'
        db.add_column(u'site_club', 'icalurl',
                      self.gf('django.db.models.fields.URLField')(max_length=400, null=True),
                      keep_default=False)

        # Adding field 'Club.icalpatterns'
        db.add_column(u'site_club', 'icalpatterns',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=100),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Club.icalurl'
        db.delete_column(u'site_club', 'icalurl')

        # Deleting field 'Club.icalpatterns'
        db.delete_column(u'site_club', 'icalpatterns')


    models = {
        u'site.club': {
            'Meta': {'ordering': "['name']", 'object_name': 'Club'},
            'contact': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True'}),
            'icalpatterns': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'icalurl': ('django.db.models.fields.URLField', [], {'max_length': '400', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        u'site.race': {
            'Meta': {'ordering': "['date', 'time']", 'object_name': 'Race'},
            'club': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['site.Club']"}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['site.RaceCourse']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'d'", 'max_length': '1'}),
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