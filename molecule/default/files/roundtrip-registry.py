# SPDX-FileCopyrightText: 2026 Slavi Pantaleev
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Pushes a tiny container image, reads it back, and tries to delete it.

Usage: roundtrip-registry.py <registry URL> <repository> <tag>

Prints a JSON report of what the registry answered at every step, so that the
Molecule verifier can assert on it rather than on this script's exit code.

Written against the registry HTTP API rather than around `docker push`/`docker
pull`, for two reasons:

- Docker only pushes what its image store holds, and a `docker push` of the
  same image under several tags gives every one of them the same manifest
  digest, which makes per-tag digest assertions meaningless. The layer here
  carries the repository and tag in it, so the image is distinct per tag.

- Recent Docker releases push OCI manifests, which answer a request for
  `application/vnd.docker.distribution.manifest.v2+json` with a 404. What a
  `docker push` produced would therefore depend on the Docker version the test
  happened to run against. Speaking the API directly pins the media type.

The round trip proves the registry is genuinely storing and serving content,
not merely answering `/v2/`: every blob is fetched back and re-hashed, and a
content-addressed store that returns the wrong bytes cannot pass that.
"""

import gzip
import hashlib
import io
import json
import sys
import tarfile
import urllib.error
import urllib.request

MANIFEST_MEDIA_TYPE = "application/vnd.docker.distribution.manifest.v2+json"

registry_url, repository, tag = sys.argv[1], sys.argv[2], sys.argv[3]


def request(url, method, body=None, content_type=None, accept=None):
    # The upload location the registry hands back may be absolute or relative.
    request_url = url if url.startswith("http") else registry_url + url

    http_request = urllib.request.Request(request_url, data=body, method=method)
    if content_type is not None:
        http_request.add_header("Content-Type", content_type)
    if accept is not None:
        http_request.add_header("Accept", accept)

    try:
        response = urllib.request.urlopen(http_request)
    except urllib.error.HTTPError as error:
        # A refusal is a result to report, not a crash: whether the registry
        # allows deletion is exactly what the verifier wants to know.
        return error.code, dict(error.headers), error.read()

    with response:
        return response.status, dict(response.headers), response.read()


def digest_of(blob):
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def expect(status, expected, what):
    if status not in expected:
        raise SystemExit("%s answered %d, expected one of %s" % (what, status, expected))


def push_blob(blob):
    status, headers, _ = request("/v2/%s/blobs/uploads/" % repository, "POST")
    expect(status, (202,), "starting a blob upload")

    status, _, _ = request(
        headers["Location"] + ("&" if "?" in headers["Location"] else "?") + "digest=" + digest_of(blob),
        "PUT",
        body=blob,
        content_type="application/octet-stream",
    )
    expect(status, (201,), "completing a blob upload")

    return digest_of(blob)


def fetch_blob(digest):
    """Fetches a blob back and re-hashes it, to prove the bytes survived."""
    status, _, body = request("/v2/%s/blobs/%s" % (repository, digest), "GET")
    expect(status, (200,), "fetching blob %s" % digest)
    return {"status": status, "size": len(body), "digest_matches": digest_of(body) == digest}


# A real (if minuscule) layer, so that this is a genuine container image rather
# than a blob the registry merely happens to hold. The marker makes the layer -
# and therefore the whole image - unique to this repository and tag.
marker = ("%s:%s\n" % (repository, tag)).encode()

layer_tar = io.BytesIO()
with tarfile.open(fileobj=layer_tar, mode="w") as archive:
    entry = tarfile.TarInfo("marker")
    entry.size = len(marker)
    archive.addfile(entry, io.BytesIO(marker))
layer = gzip.compress(layer_tar.getvalue(), mtime=0)

config = json.dumps({
    "architecture": "amd64",
    "os": "linux",
    "config": {},
    "rootfs": {"type": "layers", "diff_ids": [digest_of(layer_tar.getvalue())]},
}).encode()

config_digest = push_blob(config)
layer_digest = push_blob(layer)

manifest = json.dumps({
    "schemaVersion": 2,
    "mediaType": MANIFEST_MEDIA_TYPE,
    "config": {
        "mediaType": "application/vnd.docker.container.image.v1+json",
        "size": len(config),
        "digest": config_digest,
    },
    "layers": [{
        "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
        "size": len(layer),
        "digest": layer_digest,
    }],
}).encode()

status, _, _ = request(
    "/v2/%s/manifests/%s" % (repository, tag),
    "PUT",
    body=manifest,
    content_type=MANIFEST_MEDIA_TYPE,
)
expect(status, (201,), "pushing the manifest")

# Read the image back by tag, the way a `docker pull` would.
status, headers, body = request(
    "/v2/%s/manifests/%s" % (repository, tag), "GET", accept=MANIFEST_MEDIA_TYPE,
)
expect(status, (200,), "fetching the manifest")

manifest_digest = headers.get("Docker-Content-Digest")

# Fetched before anything is deleted, so that what these report is the result
# of the round trip rather than of the deletion attempt below.
blob_get = {"config": fetch_blob(config_digest), "layer": fetch_blob(layer_digest)}

# Deletion is by digest, never by tag. Whether this is allowed is decided by
# `REGISTRY_STORAGE_DELETE_ENABLED`, which the role writes into its env file:
# 202 when deletion is enabled, 405 UNSUPPORTED when it is not.
delete_status, _, delete_body = request(
    "/v2/%s/manifests/%s" % (repository, manifest_digest), "DELETE",
)

print(json.dumps({
    "repository": repository,
    "tag": tag,
    "pushed": {
        "manifest_digest": digest_of(manifest),
        "config_digest": config_digest,
        "layer_digest": layer_digest,
        "layer_size": len(layer),
    },
    "manifest_get": {
        "status": status,
        "digest_header": manifest_digest,
        # The registry is content-addressed, so the digest it reports has to be
        # the hash of the bytes it just handed back, and of what we pushed.
        "digest_matches_body": manifest_digest == digest_of(body),
        "digest_matches_pushed": manifest_digest == digest_of(manifest),
        "media_type": json.loads(body).get("mediaType"),
    },
    "blob_get": blob_get,
    "delete": {
        "status": delete_status,
        "body": delete_body.decode("utf-8", "replace").strip(),
    },
}, indent=2))
