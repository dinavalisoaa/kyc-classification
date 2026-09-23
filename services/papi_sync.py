"""Syncs data/kyc/<split>/<type>/ + local DB from the papi API.
Complements (does not overwrite) the dataset built by training/prepare_dataset.py from
cin-data/: run training/prepare_dataset.py or training/retrain.py --no-sync first if you
need to start from scratch.

Config (env):
    PAPI_API_URL     e.g. https://papi.mg/api/documents  (expected payload: see README)
    PAPI_API_TOKEN   auth token, if the API needs one
    PAPI_CDN_BASE    default https://cdn.papi.mg

Adapt fetch_new_documents()/confirm_sync() to the real API contract once known (filter
parameter name, pagination, isSynced confirmation method).
"""
import os

import requests

from services.database import documents_to_download, init_db, mark_downloaded, upsert_documents

API_URL = os.environ.get('PAPI_API_URL')
API_TOKEN = os.environ.get('PAPI_API_TOKEN')
CDN_BASE = os.environ.get('PAPI_CDN_BASE', 'https://cdn.papi.mg')
TARGET_DIR = 'data/kyc'
TIMEOUT = 15


def _headers():
    return {'Authorization': f'Bearer {API_TOKEN}'} if API_TOKEN else {}


def fetch_new_documents():
    # Only requests documents not yet synced (isSynced column on the papi side)
    resp = requests.get(API_URL, params={'is_synced': 'false'}, headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()['documents']


def confirm_sync(doc_id):
    # Notifies papi that the document was fetched (isSynced=true on the papi side)
    requests.patch(f'{API_URL}/{doc_id}', json={'is_synced': True}, headers=_headers(), timeout=TIMEOUT)


def download_document(doc, session):
    destination = os.path.join(TARGET_DIR, doc['split'], doc['type'])
    os.makedirs(destination, exist_ok=True)
    local_path = os.path.join(destination, os.path.basename(doc['path']))

    if not os.path.exists(local_path):
        url = doc['path'] if doc['path'].startswith('http') else f"{CDN_BASE}{doc['path']}"
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(resp.content)
    return local_path


def sync():
    """Returns a summary {ok, nouveaux, a_telecharger, telecharges, echecs, erreurs}.
    Keys stay as-is: this dict is returned as-is by the /internal/sync-papi endpoint
    and consumed by the papi backend -- an external API contract, not renamed here."""
    if not API_URL:
        print('== PAPI_API_URL not set: papi sync skipped ==')
        return {'ok': False, 'reason': 'PAPI_API_URL not set',
                'nouveaux': 0, 'a_telecharger': 0, 'telecharges': 0, 'echecs': 0}
    init_db()

    print('== Fetching new documents (papi API) ==')
    new_docs = fetch_new_documents()
    upsert_documents(new_docs)
    print(f'{len(new_docs)} new documents recorded in DB')

    downloaded_count = 0
    errors = []
    with requests.Session() as session:
        to_download = documents_to_download()
        print(f'== Downloading {len(to_download)} documents ==')
        for doc in to_download:
            try:
                local_path = download_document(doc, session)
                mark_downloaded(doc['id'], local_path)
                confirm_sync(doc['id'])
                downloaded_count += 1
            except requests.RequestException as e:
                print(f"SKIPPED document {doc['id']} ({doc['path']}): {e}")
                errors.append({'id': doc['id'], 'path': doc['path'], 'error': str(e)})

    return {'ok': True, 'nouveaux': len(new_docs), 'a_telecharger': len(to_download),
            'telecharges': downloaded_count, 'echecs': len(errors), 'erreurs': errors[:20]}


if __name__ == '__main__':
    sync()
