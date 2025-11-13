"""
SSL Certificate Investigation Tool for NITE Website

This script investigates SSL certificate issues with nite.org.il domains
and provides secure alternatives to verify=False.

Usage:
    python3 ssl_investigation.py
"""

import ssl
import socket
import requests
import urllib3
from datetime import datetime
import logging
from config import NITE_MAIN_URL, NITE_API_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress urllib3 warnings for investigation
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_certificate_details(hostname: str, port: int = 443) -> dict:
    """
    Retrieve and analyze SSL certificate details from a hostname.
    
    Returns:
        Dictionary with certificate information including:
        - issuer: Certificate issuer
        - subject: Certificate subject
        - expiry: Expiration date
        - fingerprint: Certificate fingerprint
        - certificate: PEM-encoded certificate
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                cert_obj = ssock.getpeercert()
                cert_der = ssl.DER_cert_to_PEM_cert(cert)
                
                return {
                    "hostname": hostname,
                    "issuer": dict(x[0] for x in cert_obj.get("issuer", [])),
                    "subject": dict(x[0] for x in cert_obj.get("subject", [])),
                    "expiry": datetime.strptime(cert_obj["notAfter"], "%b %d %H:%M:%S %Y %Z"),
                    "fingerprint": ssock.getpeercert(True).hex(),
                    "certificate": cert_der,
                    "success": True
                }
    except Exception as e:
        logger.error(f"Failed to get certificate for {hostname}: {e}")
        return {
            "hostname": hostname,
            "error": str(e),
            "success": False
        }


def test_request_with_verify(verify_option, description: str) -> dict:
    """
    Test HTTP request with different verify options.
    
    Args:
        verify_option: True, False, or path to certificate file
        description: Human-readable description of the test
    
    Returns:
        Dictionary with test results
    """
    session = requests.Session()
    result = {
        "description": description,
        "verify": verify_option,
        "main_url_success": False,
        "api_url_success": False,
        "main_url_error": None,
        "api_url_error": None
    }
    
    try:
        # Test main URL
        resp = session.get(
            NITE_MAIN_URL,
            timeout=10,
            verify=verify_option
        )
        result["main_url_success"] = True
        result["main_url_status"] = resp.status_code
        
        # Test API URL with headers
        from config import NITE_API_HEADERS
        resp = session.get(
            NITE_API_URL,
            headers=NITE_API_HEADERS,
            timeout=10,
            verify=verify_option
        )
        result["api_url_success"] = True
        result["api_url_status"] = resp.status_code
        result["api_response_type"] = type(resp.json()).__name__ if resp.status_code == 200 else None
        
    except requests.exceptions.SSLError as e:
        result["main_url_error" if not result["main_url_success"] else "api_url_error"] = f"SSL Error: {e}"
        logger.warning(f"{description}: SSL Error - {e}")
    except requests.exceptions.RequestException as e:
        result["main_url_error" if not result["main_url_success"] else "api_url_error"] = str(e)
        logger.warning(f"{description}: Request Error - {e}")
    
    return result


def save_certificate_to_file(cert_data: str, filename: str) -> str:
    """Save certificate to a PEM file."""
    filepath = f"/home/idoc/projects/nite_checker/{filename}"
    with open(filepath, "w") as f:
        f.write(cert_data)
    logger.info(f"Certificate saved to {filepath}")
    return filepath


def main():
    """Main investigation function."""
    logger.info("=" * 70)
    logger.info("SSL Certificate Investigation for NITE Websites")
    logger.info("=" * 70)
    
    # Extract hostnames from URLs
    main_hostname = "niteop.nite.org.il"
    api_hostname = "proxy.nite.org.il"
    
    logger.info(f"\n1. Analyzing certificates for:")
    logger.info(f"   - Main site: {main_hostname}")
    logger.info(f"   - API: {api_hostname}")
    
    # Get certificate details
    main_cert = get_certificate_details(main_hostname)
    api_cert = get_certificate_details(api_hostname)
    
    if main_cert.get("success"):
        logger.info(f"\n✓ Main site certificate:")
        logger.info(f"   Issuer: {main_cert['issuer'].get('commonName', 'Unknown')}")
        logger.info(f"   Subject: {main_cert['subject'].get('commonName', 'Unknown')}")
        logger.info(f"   Expires: {main_cert['expiry']}")
        logger.info(f"   Valid for: {(main_cert['expiry'] - datetime.now()).days} days")
        
        # Save certificate
        cert_file = save_certificate_to_file(
            main_cert['certificate'],
            "nite_main_cert.pem"
        )
    else:
        logger.error(f"\n✗ Failed to get main site certificate: {main_cert.get('error')}")
        cert_file = None
    
    if api_cert.get("success"):
        logger.info(f"\n✓ API certificate:")
        logger.info(f"   Issuer: {api_cert['issuer'].get('commonName', 'Unknown')}")
        logger.info(f"   Subject: {api_cert['subject'].get('commonName', 'Unknown')}")
        logger.info(f"   Expires: {api_cert['expiry']}")
        logger.info(f"   Valid for: {(api_cert['expiry'] - datetime.now()).days} days")
        
        # Save certificate
        api_cert_file = save_certificate_to_file(
            api_cert['certificate'],
            "nite_api_cert.pem"
        )
    else:
        logger.error(f"\n✗ Failed to get API certificate: {api_cert.get('error')}")
        api_cert_file = None
    
    # Test different verification methods
    logger.info(f"\n2. Testing different SSL verification methods:")
    logger.info("-" * 70)
    
    tests = [
        (True, "Default verification (system CA bundle)"),
        (False, "No verification (current approach - INSECURE)"),
    ]
    
    if cert_file:
        tests.append((cert_file, "Custom certificate file (main site)"))
    
    if api_cert_file and api_cert_file != cert_file:
        tests.append((api_cert_file, "Custom certificate file (API)"))
    
    # Also try certifi bundle
    try:
        import certifi
        tests.append((certifi.where(), "certifi CA bundle"))
    except ImportError:
        logger.warning("certifi package not installed")
    
    results = []
    for verify_option, description in tests:
        logger.info(f"\nTesting: {description}")
        result = test_request_with_verify(verify_option, description)
        results.append(result)
        
        if result["main_url_success"] and result["api_url_success"]:
            logger.info(f"  ✓ Both URLs accessible with this method")
        elif result["main_url_success"]:
            logger.info(f"  ⚠ Main URL OK, API URL failed: {result.get('api_url_error')}")
        elif result["api_url_success"]:
            logger.info(f"  ⚠ API URL OK, Main URL failed: {result.get('main_url_error')}")
        else:
            logger.info(f"  ✗ Both failed")
    
    # Summary and recommendations
    logger.info(f"\n3. Summary and Recommendations:")
    logger.info("=" * 70)
    
    working_methods = [
        r for r in results 
        if r["main_url_success"] and r["api_url_success"]
    ]
    
    if working_methods:
        logger.info(f"\n✓ Found {len(working_methods)} working secure method(s):")
        for result in working_methods:
            if result["verify"] is not False:
                logger.info(f"\n  RECOMMENDED: {result['description']}")
                if isinstance(result["verify"], str):
                    logger.info(f"    Use: verify='{result['verify']}'")
                else:
                    logger.info(f"    Use: verify=True (default)")
    else:
        logger.warning("\n⚠ No secure methods worked. Investigating root cause...")
        
        # Check what specific SSL errors occur
        logger.info("\n  Trying to identify the SSL error:")
        try:
            test_request_with_verify(True, "Error analysis")
        except Exception as e:
            logger.error(f"    Error type: {type(e).__name__}")
            logger.error(f"    Error message: {str(e)}")
            
            # Provide specific guidance based on error
            if "certificate verify failed" in str(e).lower():
                logger.info("\n  Possible solutions:")
                logger.info("    1. Update system CA certificates:")
                logger.info("       sudo apt-get update && sudo apt-get install ca-certificates")
                logger.info("    2. Update certifi package:")
                logger.info("       pip install --upgrade certifi")
                logger.info("    3. Use the saved certificate file with verify parameter")
    
    logger.info("\n" + "=" * 70)
    logger.info("Investigation complete!")
    
    return results, main_cert, api_cert


if __name__ == "__main__":
    main()

