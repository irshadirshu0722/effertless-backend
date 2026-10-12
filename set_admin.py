import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase Admin using your service-account credentials.
cred = credentials.Certificate("gcp-service-account.json")

app = firebase_admin.initialize_app(
    cred,
    {"projectId": "effortless-7d9e9"},
)

# Replace this with the admin's actual Firebase UID.
admin_uid = "4aBmgCMlYZPDDaeRwJIIYZCzJAD2"

auth.set_custom_user_claims(
    admin_uid,
    {"role": "admin"},
)

print("Admin role assigned successfully.")