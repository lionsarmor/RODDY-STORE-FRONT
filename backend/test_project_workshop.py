import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from backend.project_workshop import register_project_workshop


class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        library = self.root / 'library'
        (library / 'Project/files').mkdir(parents=True)
        (library / 'Project/OPEN_ME.html').write_text('<img src="files/render.svg"><a href="files/">Files</a>')
        (library / 'Project/files/render.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (library / 'Project/files/bom.csv').write_text('Part,Qty\nTest,1')
        (library / 'unlisted.txt').write_text('must not be exposed')
        (self.root / 'secret.txt').write_text('private outside library')
        (library / 'escape.txt').symlink_to(self.root / 'secret.txt')
        self.manifest = {'updatedAt':'2026-10-16T00:00:00Z', 'projects':[],
                         'entries':[{'id':'test','path':'Project/OPEN_ME.html'}],
                         'files':dict.fromkeys(['Project/OPEN_ME.html','Project/files/render.svg','Project/files/bom.csv','escape.txt'], {})}
        (library / 'manifest.json').write_text(json.dumps(self.manifest))
        app = FastAPI()
        def owner(request):
            if request.headers.get('Authorization') != 'Bearer owner':
                raise HTTPException(401)
        register_project_workshop(app, owner, self.root)
        self.client = TestClient(app)

    def issue(self):
        response = self.client.post('/admin/workshop/open', json={'id':'test'}, headers={'Authorization':'Bearer owner'})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['path']

    def test_owner_access_required_and_listing_is_small(self):
        self.assertEqual(self.client.get('/admin/workshop').status_code, 401)
        self.assertEqual(self.client.post('/admin/workshop/open', json={'id':'test'}).status_code, 401)
        response = self.client.get('/admin/workshop', headers={'Authorization':'Bearer owner'})
        self.assertNotIn('files', response.json())
        self.assertEqual(response.json()['entries'], self.manifest['entries'])
        self.assertEqual(self.client.post('/admin/workshop/open', json={'id':'../../secret'}, headers={'Authorization':'Bearer owner'}).status_code, 404)
        self.assertEqual(self.client.post('/admin/workshop/open', json=[], headers={'Authorization':'Bearer owner'}).status_code, 404)

    def test_relative_assets_directory_navigation_and_downloads(self):
        path = self.issue()
        document = self.client.get(path)
        self.assertEqual(document.status_code, 200)
        self.assertIn('text/html', document.headers['content-type'])
        self.assertEqual(document.headers['referrer-policy'], 'no-referrer')
        self.assertIn('no-store', document.headers['cache-control'])
        self.assertIn('sandbox', document.headers['content-security-policy'])
        base = path.rsplit('/', 1)[0]
        image = self.client.get(base+'/files/render.svg')
        self.assertEqual(image.status_code, 200)
        self.assertIn('image/svg+xml', image.headers['content-type'])
        self.assertIn('bom.csv', self.client.get(base+'/files').text)
        self.assertEqual(self.client.get(base+'/files/bom.csv').text, 'Part,Qty\nTest,1')
        self.assertEqual(self.client.get(base+'/').content, document.content)

    def test_expiry_traversal_unlisted_files_and_symlinks(self):
        path = self.issue(); prefix = path.split('/Project/')[0]
        for name in ('unlisted.txt', 'manifest.json', 'sessions.sqlite3', 'escape.txt', '%2E%2E/secret.txt', '%5Csecret.txt'):
            self.assertEqual(self.client.get(prefix+'/'+name).status_code, 404, name)
        self.assertEqual(self.client.get('/workshop/view/'+'x'*43+'/Project/OPEN_ME.html').status_code, 410)
        with patch('backend.project_workshop.time.time', return_value=99999999999):
            response = self.client.get(path)
        self.assertEqual(response.status_code, 410)
        self.assertIn('Project Workshop', response.text)
        with sqlite3.connect(self.root/'sessions.sqlite3') as db:
            digest = db.execute('SELECT digest FROM sessions').fetchone()[0]
        token = path.split('/')[3]
        self.assertEqual(digest, hashlib.sha256(token.encode()).hexdigest())

    def test_not_uploaded_is_clear(self):
        (self.root/'library/manifest.json').unlink()
        response = self.client.get('/admin/workshop', headers={'Authorization':'Bearer owner'})
        self.assertEqual(response.status_code, 503)
