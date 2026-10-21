"""Read the current host-side distribution package."""
import hashlib,json,zipfile

def sha(data):return hashlib.sha256(data).hexdigest()

def read_package(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        data = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(data.pop('MANIFEST.JSN'))
    assert set(data) == set(manifest['files'])
    for name, row in manifest['files'].items():
        assert sha(data[name]).lower() == row['sha256'].lower(), name
    return data


