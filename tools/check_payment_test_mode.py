"""Secret-safe configuration preflight. No provider requests or payments."""
import argparse
import json
import os
from pathlib import Path


def inspect_config(key: str, shop_id: str) -> dict:
    mode = 'test' if key.startswith('test_') else 'live' if key.startswith('live_') else 'unknown'
    plausible = len(key) >= 24
    ready = mode == 'test' and plausible and bool(shop_id.strip())
    reason = ('TEST_CONFIGURATION_PRESENT_NOT_PROVIDER_VERIFIED' if ready else
              'LIVE_KEY_NOT_ALLOWED_FOR_NO_CHARGE_TEST' if mode == 'live' else
              'TEST_SHOP_CONFIGURATION_INCOMPLETE' if mode == 'test' else
              'KEY_MODE_UNKNOWN_OR_ABSENT')
    return {'status': reason, 'key_present': bool(key), 'key_mode': mode,
            'shop_id_present': bool(shop_id.strip()), 'test_configuration_present': ready,
            'provider_verified': False, 'provider_requests': 0, 'payments_created': 0,
            'real_charges': 0, 'secret_value_disclosed': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect_config(os.environ.get('NSP_PAYMENT_KEY', ''),
                            os.environ.get('NSP_PAYMENT_SHOP_ID', ''))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
