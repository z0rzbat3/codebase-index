"""
Docker Compose YAML parser for codebase_index.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from codebase_index.config import HAS_YAML, yaml
from codebase_index.parsers.base import BaseParser, ParserRegistry

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


@ParserRegistry.register("docker", ["docker-compose.yaml", "docker-compose.yml"])
class DockerParser(BaseParser):
    """
    Docker Compose parser using PyYAML.

    Falls back to regex parsing if PyYAML is not available.
    """

    supports_fallback = True

    def scan(self, filepath: Path) -> dict[str, Any]:
        """
        Scan a docker-compose file.

        Args:
            filepath: Path to the docker-compose file.

        Returns:
            Dictionary with services, networks, and volumes.
        """
        if not HAS_YAML:
            logger.debug("PyYAML not available, using regex fallback for %s", filepath)
            return self._scan_regex(filepath)

        result: dict[str, Any] = {
            "services": [],
            "networks": [],
            "volumes": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return {"error": str(e)}
        except yaml.YAMLError as e:
            logger.warning("Invalid YAML in %s: %s", filepath, e)
            return {"error": f"Invalid YAML: {e}"}

        if not data:
            return result

        # Services
        services = data.get("services", {})
        for name, config in services.items():
            if not isinstance(config, dict):
                continue

            environment = config.get("environment", {})
            env_keys: list[str] = []
            if isinstance(environment, dict):
                env_keys = list(environment.keys())
            elif isinstance(environment, list):
                env_keys = environment

            service_info: dict[str, Any] = {
                "name": name,
                "image": config.get("image"),
                "build": config.get("build"),
                "ports": config.get("ports", []),
                "depends_on": config.get("depends_on", []),
                "environment": env_keys,
            }
            result["services"].append(service_info)

        # Networks
        networks = data.get("networks", {})
        result["networks"] = list(networks.keys()) if networks else []

        # Volumes
        volumes = data.get("volumes", {})
        result["volumes"] = list(volumes.keys()) if volumes else []

        return result

    def _scan_regex(self, filepath: Path) -> dict[str, Any]:
        """Fallback regex scanning if YAML not available."""
        result: dict[str, Any] = {
            "services": [],
            "networks": [],
            "volumes": [],
            "_fallback": "regex",
        }

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, IOError) as e:
            logger.warning("Could not read %s: %s", filepath, e)
            return result

        # Simple service detection
        in_services = False
        for line in content.split("\n"):
            if re.match(r"^services:\s*$", line):
                in_services = True
                continue
            if in_services and re.match(r"^[a-z]", line):
                in_services = False
            if in_services:
                match = re.match(r"^\s{2}(\w+):\s*$", line)
                if match:
                    result["services"].append({"name": match.group(1)})

        return result


# Override the extension-based registration to use filename matching
# Docker files are matched by filename, not extension
def _get_docker_parser(filepath: Path) -> tuple[DockerParser | None, str | None]:
    """Check if file is a docker-compose file."""
    name = filepath.name.lower()
    if name in ("docker-compose.yaml", "docker-compose.yml"):
        return DockerParser(), "docker"
    if "docker" in name and filepath.suffix.lower() in (".yaml", ".yml"):
        return DockerParser(), "docker"
    return None, None


# Store reference to the docker parser checker
DockerParser.get_for_file = staticmethod(_get_docker_parser)  # type: ignore
