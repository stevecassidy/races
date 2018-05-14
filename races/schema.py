import graphene

import races.apps.cabici.schema


class Query(races.apps.cabici.schema.Query, graphene.ObjectType):
    # This class will inherit from multiple Queries
    # as we begin to add more apps to our project
    pass


schema = graphene.Schema(query=Query)