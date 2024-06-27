import firebase_admin
from google.cloud import firestore
from google.oauth2 import service_account
from firebase_admin import storage, credentials

_authenticated = False

_firebase_credentials = {
    "your firebase credentials"
}

_credentials = service_account.Credentials.from_service_account_info(info=_firebase_credentials)
firestore_db = firestore.Client(credentials=_credentials)


def authenticate_with_firebase():
    global _authenticated
    if _authenticated:
        return

    # Authenticate with Firestore.
    cred = credentials.Certificate(_firebase_credentials)
    firebase_admin.initialize_app(cred)

    _authenticated = True


def upload_filestream_to_firebase(file_stream, file_name, content_type):
    authenticate_with_firebase()
    bucket = storage.bucket()
    blob = bucket.blob(file_name)
    blob.upload_from_file(file_stream, content_type=content_type)
    blob.make_public()
    return blob.public_url
