"""GCP Cloud Run scaling tools — The 'Ops Hand' of the SRE Agent.

Provides tools for immediate infrastructure mitigation when Dynatrace
detects resource exhaustion (CPU spikes, memory pressure, etc.).
"""

import logging
from typing import Optional

import google.auth
from google.cloud import run_v2

from sre_agent.config import get_settings

logger = logging.getLogger(__name__)


def scale_cloud_run_service(
    service_name: str,
    max_instances: int = 5,
    region: Optional[str] = None,
) -> dict:
    """Scale a Google Cloud Run service by updating its maximum instance count.

    Use this tool when the Dynatrace trace analysis indicates resource
    exhaustion such as CPU usage above 90%, high memory pressure, or
    traffic overload causing service degradation.

    Args:
        service_name: The name of the Cloud Run service to scale.
        max_instances: The new maximum number of instances (default: 5).
        region: GCP region where the service is deployed. If not provided,
                uses the default region from configuration.

    Returns:
        A dictionary containing:
        - success (bool): Whether the scaling operation succeeded
        - service (str): The full service name
        - previous_max_instances (int): Previous max instance count
        - new_max_instances (int): Updated max instance count
        - message (str): Human-readable status message
    """
    settings = get_settings()
    project_id = settings.gcp_project_id
    region = region or settings.gcp_region

    if not project_id:
        return {
            "success": False,
            "service": service_name,
            "message": "GCP_PROJECT_ID is not configured. Cannot scale service.",
        }

    full_service_name = (
        f"projects/{project_id}/locations/{region}/services/{service_name}"
    )

    try:
        # Authenticate using Application Default Credentials
        credentials, _ = google.auth.default()
        client = run_v2.ServicesClient(credentials=credentials)

        # Get current service configuration
        service = client.get_service(name=full_service_name)
        previous_max = (
            service.template.scaling.max_instance_count
            if service.template.scaling
            else 0
        )

        # Update scaling configuration
        service.template.scaling.max_instance_count = max_instances

        # Apply the update
        operation = client.update_service(service=service)
        result = operation.result()  # Wait for completion

        message = (
            f"Successfully scaled '{service_name}' from {previous_max} to "
            f"{max_instances} max instances in {region}."
        )
        logger.info(f"☁️  {message}")

        return {
            "success": True,
            "service": full_service_name,
            "previous_max_instances": previous_max,
            "new_max_instances": max_instances,
            "message": message,
        }

    except Exception as e:
        error_msg = f"Failed to scale service '{service_name}': {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "service": full_service_name,
            "message": error_msg,
        }
