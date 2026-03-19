---
sidebar_position: 2
---

# GET /health

Check backend health and data freshness. This endpoint requires no authentication and accepts no parameters.

## Request

```
GET /health
```

## Response

```json
{
  "status": "ok",
  "version": "2.0.0",
  "data_files_loaded": 10,
  "data_freshness": {
    "air-quality.json": "2026-01-06T06:12:31Z",
    "cost-of-living.json": "2026-01-06T06:14:05Z",
    "hospital-quality.json": "2026-01-06T06:13:22Z",
    "health-demographics.json": "2026-01-06T06:11:58Z",
    "donor-registration.json": "2026-01-06T06:10:44Z",
    "traffic-fatalities.json": "2025-10-14T06:09:12Z",
    "wait-time-distributions.json": "2025-11-01T00:00:00Z",
    "competing-risks.json": "2025-11-01T00:00:00Z",
    "cause-of-death-by-region.json": "2026-02-15T00:00:00Z",
    "srtr-center-mapping.json": "2025-11-01T00:00:00Z"
  }
}
```

### HealthResponse Schema

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `status` | string | `ok` `degraded` | Overall backend status |
| `version` | string | varies | Backend version |
| `data_files_loaded` | integer | varies | Number of data files loaded at startup |
| `data_freshness` | object | varies | `{ filename: iso_timestamp }` for each loaded file |

A status of `ok` means all data files loaded successfully and the simulation is ready to run. A status of `degraded` means some data files are missing or failed to load; the simulation may fall back to default parameters in that case.

## Usage

The `session.js` frontend module polls `/health` for two purposes. First, it detects whether the backend is running and shows the session bar accordingly. Second, it verifies that data is loaded before offering Phase 2 simulation to the user.

## Example

```bash
curl http://localhost:8002/health
```
