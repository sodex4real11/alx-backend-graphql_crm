INSTALLED_APPS = [
    # default Django apps...
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # GraphQL and custom apps
    'graphene_django',
    'crm',
]

# Optional: Graphene settings
GRAPHENE = {
    'SCHEMA': 'alx_backend_graphql_crm.schema.schema'
}
