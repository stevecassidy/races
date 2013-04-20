from races.settings.base import *

DEBUG = False
TEMPLATE_DEBUG = False

INSTALLED_APPS += ('sentry,')

DATABASES['default']['NAME'] = 'races_production'

SENTRY_LOG_DIR = os.path.join(PROJECT_DIR, 'logs')
SENTRY_RUN_DIR= os.path.join(PROJECT_DIR, 'run')
SENTRY_WEB_HOST = '127.0.0.1'
SENTRY_WEB_PORT = 9000
SENTRY_KEY = '^g=q21r_nnmbz49d!vs*2gvpll-y9b@&amp;t3k2r3c$*u&amp;2la5!%s'

SENTRY_FILTERS = (
    'sentry.filters.StatusFilter',
    'sentry.filters.LoggerFilter',
    'sentry.filters.LevelFilter',
    'sentry.filters.ServerNameFilter',
    'sentry.filters.SiteFilter',
)

SENTRY_VIEWS = (
    'sentry.views.Exception',
    'sentry.views.Message',
    'sentry.views.Query',
)


