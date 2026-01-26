"""FedEx PCS service code to rate service mapping."""

# Maps PCS extkey (pcs_shipping_provider) to rate service
SERVICE_MAPPING = {
    # Ground Economy (SmartPost)
    "FXESPPS": "Ground Economy",
    "FXEGRD": "Ground Economy",
    "FXESPPSL": "Ground Economy",

    # Home Delivery
    "FXE2D": "Home Delivery",
    "FXE2DXLBOR": "Home Delivery",
    "FXE2DTBOR": "Home Delivery",
    "FXESTDO": "Home Delivery",
    "FXEINTECON": "Home Delivery",
    "FXEINTPRIO": "Home Delivery",
    "FXEPO": "Home Delivery",
    "FXE2DSBOR": "Home Delivery",
    "FXEHD": "Home Delivery",
    "FXE2DLBOR": "Home Delivery",
    "FXE2DMBOR": "Home Delivery",
    "FXE2DENVOR": "Home Delivery",
    "FXE2DPAKOR": "Home Delivery",
}


def get_rate_service(pcs_service_code: str) -> str:
    """Map PCS service code to rate service (Home Delivery or Ground Economy)."""
    return SERVICE_MAPPING.get(pcs_service_code, "Home Delivery")  # Default to HD
