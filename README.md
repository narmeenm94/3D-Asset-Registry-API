# METRO 3D Asset Registry API

REST API for managing 3D visualization assets in the DTRIP4H project. Built with FastAPI, it handles upload, search, versioning, and metadata for 3D models used across the consortium's research infrastructure nodes.

Part of [DTRIP4H](https://dtrip4h.eu/) Work Package 9 — developed by METRO (Metropolia Ammattikorkeakoulu OY).

---

## What it does

- Stores and serves 3D assets (glTF, GLB, USDZ, OBJ, STL, PLY, Blender, FBX)
- Automatically extracts geometry metadata (triangle counts, bounding boxes, materials, etc.) from uploaded files
- Provides JSON-LD / RDF metadata output for federated discovery across DTRIP4H nodes
- Handles versioning — every file update creates an immutable version record
- Enforces a 6-level permission model (private → group → institution → consortium → approval required → public)
- Authenticates via DDTE-issued JWT tokens in production; ships with a dev mode that bypasses auth for local testing
- Runs on PostgreSQL + S3-compatible storage in production, falls back to SQLite + local filesystem for development

## Quick start

### Local development (no database setup needed)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 5000
```

That's it. The API detects that PostgreSQL isn't available and automatically falls back to SQLite. You'll see a warning in the console — that's expected.

- API: http://localhost:5000
- Interactive docs: http://localhost:5000/docs

### With Docker

```bash
cd docker
docker-compose up -d
```

This spins up the API, PostgreSQL, and MinIO (S3-compatible object storage).

- API: http://localhost:8000
- MinIO console: http://localhost:9001 (minioadmin / minioadmin)

### Local dev with external PostgreSQL + MinIO

```bash
python -m venv venv
venv\Scripts\activate        # Linux/Mac: source venv/bin/activate

pip install -r requirements.txt

cd docker
docker-compose -f docker-compose.local.yml up -d   # starts only PG + MinIO

cp .env.example .env         # edit with your settings
alembic upgrade head         # run migrations

uvicorn app.main:app --reload --port 8000
```

## Endpoints

Base path: `/api/v1`

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/assets` | Search and list assets (paginated, filterable) |
| GET | `/assets/{id}` | Get asset metadata (supports `Accept: application/ld+json`) |
| GET | `/assets/{id}/file` | Download the 3D file |
| POST | `/assets` | Upload a new asset (multipart form) |
| PUT | `/assets/{id}/file` | Upload a new version |
| PATCH | `/assets/{id}` | Update name/description |
| PUT | `/assets/{id}/tags` | Replace tags |
| DELETE | `/assets/{id}` | Delete asset and all versions |
| GET | `/assets/{id}/versions` | List version history |
| GET | `/tags` | List all tags with usage counts |
| GET | `/health` | Health check (shows DB status) |
| GET | `/metrics` | Request/error/storage metrics (JSON) |
| GET | `/metrics/prometheus` | Same metrics in Prometheus text format |

### Upload example

```bash
curl -X POST http://localhost:5000/api/v1/assets \
  -F "file=@molecule.glb" \
  -F "name=CYP3A4_vdw" \
  -F "format=glb" \
  -F "description=Van der Waals surface of CYP3A4" \
  -F "tags=UC2,molecule,pharmaceutical" \
  -F "scientificDomain=pharmaceutical-sciences" \
  -F "accessLevel=consortium"
```

Triangle count, bounding box, materials, and other geometry metadata are extracted automatically from the file. Pass `autoExtract=false` to skip that.

### JSON-LD output

```bash
curl http://localhost:5000/api/v1/assets/{id} \
  -H "Accept: application/ld+json"
```

Returns the full RDF metadata using DCAT, Dublin Core, Schema.org, and the custom METRO vocabulary — ready for federated catalog harvesting.

## Auto-extracted metadata

When you upload a glTF/GLB file, the API parses it with `trimesh` and `pygltflib` and pulls out:

- Triangle and vertex counts
- Bounding box coordinates and dimensions
- Material names and counts
- Animation and texture info
- Mesh topology (watertight check)
- Generator tool name

For OBJ/STL/PLY, you get geometry data (triangles, vertices, bounding box). USDZ gets basic parsing. Blender and FBX files are stored as-is.

## Authentication

In **dev mode** (`DEV_MODE=true`, the default), authentication is bypassed — all requests run as a mock user.

In **production**, the API validates JWT tokens issued by the DDTE authentication service:
1. Fetches JWKS from the configured DDTE endpoint
2. Validates signature, expiry, issuer, and audience
3. Checks scopes (`assets:read`, `assets:write`)
4. Enforces per-asset permissions based on the 6-level access hierarchy

## Permission levels

| Level | Who can access |
|-------|---------------|
| Private | Owner only |
| Group | Specific users or institutions listed on the asset |
| Institution | Anyone from the owner's institution |
| Consortium | Any DTRIP4H member |
| Approval Required | Users explicitly approved by the owner |
| Public | Any authenticated user |

Write and delete operations always require ownership.

## Configuration

Key environment variables (see `env.example` for the full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (SQLite fallback) | PostgreSQL connection string |
| `STORAGE_BACKEND` | `local` | `local`, `s3`, or `azure` |
| `DEV_MODE` | `true` | Bypass JWT auth for development |
| `MAX_UPLOAD_SIZE` | 500 MB | Max file upload size |
| `DDTE_JWKS_URL` | — | DDTE JWKS endpoint for token validation |
| `HOSTING_NODE` | `local-dev-node` | Node identifier for federated metadata |

## Running tests

```bash
pytest                                    # all tests
pytest --cov=app --cov-report=html        # with coverage report
pytest tests/test_api/test_assets.py -v   # specific test file
```

## Project layout

```
app/
├── api/v1/          # Endpoint handlers
├── auth/            # JWT validation, scopes, per-asset permissions
├── core/            # Exception classes, response helpers
├── db/              # SQLAlchemy engine + session setup
├── models/          # Asset, AssetVersion, Tag models
├── schemas/         # Pydantic validation + JSON-LD context/transform
├── services/        # Business logic (CRUD, metadata extraction, metrics)
└── storage/         # Local / S3 / Azure storage backends
docker/              # Dockerfile + docker-compose configs
migrations/          # Alembic migration scripts
tests/               # pytest test suite
```

## Funding

This project has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement No. [EU101188432].

---

© 2025 METRO (Metropolia Ammattikorkeakoulu OY)
