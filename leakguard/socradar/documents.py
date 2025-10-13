# socradar/documents.py
# OpenSearch integration disabled - requires OpenSearch server running
# Uncomment when you have OpenSearch/Elasticsearch running

# from django.contrib.auth import get_user_model
# from django_opensearch_dsl import Document, fields
# from django_opensearch_dsl.registries import registry
# from .models import MonitoredCredential, CredentialLeak

# User = get_user_model()

# @registry.register_document
# class UserDocument(Document):
#     username    = fields.TextField()
#     email       = fields.KeywordField()          # exact match / aggregations
#     email_text  = fields.TextField(attr="email") # full-text on same value
#     is_active   = fields.BooleanField()
#     date_joined = fields.DateField()             # ok for DateTimeField

#     class Index:
#         name = "users"
#         settings = {"number_of_shards": 1, "number_of_replicas": 0}

#     class Django:
#         model = User
#         fields = []  # we declared fields explicitly above


# @registry.register_document
# class MonitoredCredentialDocument(Document):
#     # optional: index FK as integer for filtering
#     owner = fields.IntegerField(attr="owner_id", required=False)

#     class Index:
#         name = "monitored_credentials_v1"
#         settings = {"number_of_shards": 1, "number_of_replicas": 0}
#         auto_refresh = True

#     class Django:
#         model = MonitoredCredential
#         # must match actual model fields
#         fields = ["email", "username", "domain", "created_at"]


# @registry.register_document
# class CredentialLeakDocument(Document):
#     # JSON list
#     tags = fields.ListField(fields.KeywordField())
#     user = fields.IntegerField(attr="user_id")  # optional: FK as int

#     class Index:
#         name = "leaks_v1"
#         settings = {"number_of_shards": 1, "number_of_replicas": 0}
#         auto_refresh = True

#     class Django:
#         model = CredentialLeak
#         fields = [
#             "cred_type",
#             "value",
#             "source",
#             "source_url",
#             "leak_date",
#             "severity",
#             "plaintext",
#             "content",
#             "created_at",
#             # 'tags' is declared above
#         ]
