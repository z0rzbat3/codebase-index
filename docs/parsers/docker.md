# Docker Parser Module

> Auto-generated from `codebase_index/parsers/docker.py`

## Overview

Docker Compose YAML parser for codebase-index. Extracts service definitions, networks, and volumes from docker-compose files.

## Classes

### `DockerParser`

Docker Compose parser using PyYAML. Falls back to regex parsing if PyYAML is not available.

**Attributes:**
- `supports_fallback = True`: Supports regex fallback when YAML library unavailable

**Registration:** `@ParserRegistry.register("docker", ["docker-compose.yaml", "docker-compose.yml"])`

#### Methods

- `scan(filepath: Path) -> dict[str, Any]`: Scan a docker-compose file.

  **Returns dict with:**
  - `services`: List of service definitions with name, image, build, ports, depends_on, environment
  - `networks`: List of network names
  - `volumes`: List of volume names
  - `error`: Error message if parsing failed

- `_scan_regex(filepath: Path) -> dict[str, Any]`: Fallback regex scanning when YAML not available. Returns basic service names only.

## Functions

### `_get_docker_parser(filepath: Path) -> tuple[DockerParser | None, str | None]`

Check if file is a docker-compose file by filename matching. Matches:
- `docker-compose.yaml`
- `docker-compose.yml`
- Any `.yaml`/`.yml` file with "docker" in the name

## Output Structure

```python
{
    "services": [
        {
            "name": "web",
            "image": "nginx:latest",
            "build": "./app",
            "ports": ["80:80"],
            "depends_on": ["db"],
            "environment": ["DEBUG", "API_KEY"]
        }
    ],
    "networks": ["frontend", "backend"],
    "volumes": ["data", "logs"]
}
```

## Usage

```python
from codebase_index.parsers.docker import DockerParser

parser = DockerParser()
result = parser.scan(Path("docker-compose.yml"))

for service in result["services"]:
    print(f"Service: {service['name']}")
    if service.get("image"):
        print(f"  Image: {service['image']}")
    if service.get("ports"):
        print(f"  Ports: {service['ports']}")
```

## Dependencies

- `PyYAML` (optional): For YAML parsing. Falls back to regex if unavailable.

---
*Source: codebase_index/parsers/docker.py | Lines: 143*
