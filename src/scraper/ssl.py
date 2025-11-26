"""TODO"""
import base64
import ssl
import os

import requests
import certifi
from src.logger import Logger

logger = Logger("ssl_checker")

class SSLChecker:
    """TODO"""
    def __init__(self):
        self.cert_folder = "certificates"

    def test_ssl_methods(self, url: str, verbose: bool = False):
        """Test different SSL verification methods"""
        if verbose:
            print(f"\n🔍 Testing SSL connection to: {url}")
            print("=" * 60)

        methods = [
            ("certifi bundle", certifi.where())
        ]

        results = {}

        for name, verify_option in methods:
            if verbose:
                print(f"\n📋 Testing: {name}")
            try:
                response = requests.get(url, verify=verify_option, timeout=10)
                if verbose:
                    print(f"✅ SUCCESS - Status: {response.status_code}")
                results[name] = True
            except requests.exceptions.SSLError as e:
                if verbose:
                    print(f"❌ SSL ERROR: {e}")
                results[name] = False
            except Exception as e:
                if verbose:
                    print(f"❌ OTHER ERROR: {e}")
                results[name] = False

        return results

    def analyze_certificate(self, cert_path: str):
        """Analyze a certificate file"""
        print(f"\n🔬 Analyzing certificate: {cert_path}")
        print("=" * 60)

        try:
            with open(cert_path, 'rb') as f:
                content = f.read()

            if content.startswith(b'-----BEGIN CERTIFICATE-----'):
                print("✅ Valid PEM format")

                # Try to decode the certificate
                try:
                    # Extract the certificate data
                    cert_data = content.decode('utf-8')
                    cert_lines = [
                        line
                        for line in cert_data.split("\n")
                        if line and not line.startswith("-----")
                    ]
                    cert_der = base64.b64decode(''.join(cert_lines))

                    # Parse the certificate
                    cert = ssl.DER_cert_to_PEM_cert(cert_der)
                    print("✅ Certificate is valid and parseable")

                    # Extract some basic info
                    lines = cert.split('\n')
                    for line in lines:
                        if 'Subject:' in line:
                            print(f"📋 Subject: {line.strip()}")
                        elif 'Issuer:' in line:
                            print(f"📋 Issuer: {line.strip()}")

                except Exception as e:
                    print(f"⚠️  Certificate parsing warning: {e}")

            else:
                print("❌ Invalid PEM format")
                return False

        except Exception as e:
            print(f"❌ Error reading certificate: {e}")
            return False

        return True

    def check_certificate_files(self):
        """Check for existing certificate files"""
        print("\n📁 Checking certificate files...")
        print("=" * 60)

        cert_paths = [
            f"{self.cert_folder}/mangafire_to.pem"
        ]

        found_certs = []
        for path in cert_paths:
            if os.path.exists(path):
                print(f"✅ Found: {path}")
                found_certs.append(path)
            else:
                print(f"❌ Not found: {path}")

        return found_certs

    def update_certificate_bundle(self, cert_path: str) -> bool:
        """
        Safely update the certificate bundle with a new certificate.

        Args:
            cert_path: Path to the certificate file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(cert_path):
                logger.error(f"Certificate file not found: {cert_path}")  # pylint: disable=logging-fstring-interpolation
                return False

            # Read the new certificate
            with open(cert_path, 'rb') as infile:
                new_cert = infile.read()

            # Validate that it's a valid PEM certificate
            if not new_cert.startswith(b'-----BEGIN CERTIFICATE-----'):
                logger.error("Invalid certificate format. Expected PEM format.")
                return False

            # Backup the original certifi bundle
            certifi_path = certifi.where()
            backup_path = certifi_path + '.backup'
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(certifi_path, backup_path)
                logger.info(f"Created backup of certifi bundle at {backup_path}")  # pylint: disable=logging-fstring-interpolation

            # Append the new certificate to the bundle
            with open(certifi_path, 'ab') as outfile:
                outfile.write(b'\n' + new_cert + b'\n')

            logger.info(f"Successfully added certificate from {cert_path} to certifi bundle")  # pylint: disable=logging-fstring-interpolation
            return True

        except Exception as e:
            logger.error(f"Failed to update certificate bundle: {e}")  # pylint: disable=logging-fstring-interpolation
            return False

    def main(self):
        """Main function"""
        found_certs = self.check_certificate_files()
        for cert_path in found_certs:
            self.analyze_certificate(cert_path)


if __name__ == "__main__":
    ssl_checker = SSLChecker()
    ssl_checker.main()