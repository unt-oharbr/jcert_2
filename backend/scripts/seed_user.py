"""Create her Cognito account. Run once, by hand, after the backend is deployed.

There's no sign-up page on purpose (see the brief's privacy section) — an
account only ever gets created by a parent running this script. It only
touches Cognito: her nickname/avatar/colour-theme profile is set the first
time she logs in and the app finds no profile record yet, not here — that
split is deliberate, so the account is parent-controlled but the profile is
hers.

Usage:
    uv run python scripts/seed_user.py \\
        --user-pool-id eu-west-1_XXXXXXXXX \\
        --email her@example.com \\
        --username her-username

In a real terminal this prompts for the PIN with input hidden. Some
non-interactive shells (no controllable TTY) can't support a hidden prompt
at all — in that case, set AXIOM_SEED_PIN in the environment instead and
the script uses that, skipping the prompt.
"""

from __future__ import annotations

import argparse
import getpass
import os

import boto3


def _read_pin() -> str:
    env_pin = os.environ.get("AXIOM_SEED_PIN")
    if env_pin:
        return env_pin

    pin = getpass.getpass("Set her login PIN (6+ digits, she can't see this as you type): ")
    confirm = getpass.getpass("Confirm PIN: ")
    if pin != confirm:
        raise SystemExit("PINs didn't match — nothing was created.")
    return pin


def seed_user(*, user_pool_id: str, username: str, email: str, region: str) -> None:
    client = boto3.client("cognito-idp", region_name=region)

    pin = _read_pin()
    if len(pin) < 6 or not pin.isdigit():
        raise SystemExit("PIN must be at least 6 digits.")

    client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
        ],
        MessageAction="SUPPRESS",  # no invite email — you're handing her the PIN directly
    )
    client.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=username,
        Password=pin,
        Permanent=True,
    )
    print(f"Account created for '{username}'. She can log in with that username/email and the PIN you set.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-pool-id", required=True, help="From the AxiomBackendStack CloudFormation output")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--region", default="eu-west-1")
    args = parser.parse_args()

    seed_user(user_pool_id=args.user_pool_id, username=args.username, email=args.email, region=args.region)


if __name__ == "__main__":
    main()
