import json
import os
import urllib.request

import boto3


def handler(event, context):
    sm = boto3.client("secretsmanager")
    secret = json.loads(
        sm.get_secret_value(SecretId=os.environ["SYNTHETIC_CREDENTIALS_SECRET_ARN"])[
            "SecretString"
        ]
    )

    cognito = boto3.client("cognito-idp")
    auth_resp = cognito.admin_initiate_auth(
        UserPoolId=secret["user_pool_id"],
        ClientId=secret["client_id"],
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": secret["username"],
            "PASSWORD": secret["password"],
        },
    )
    id_token = auth_resp["AuthenticationResult"]["IdToken"]

    api_url = os.environ["API_URL"].rstrip("/")
    health_ok = _http_get(f"{api_url}/health")
    props_ok = _http_get(
        f"{api_url}/properties", {"Authorization": f"Bearer {id_token}"}
    )
    success = health_ok and props_ok

    boto3.client("cloudwatch").put_metric_data(
        Namespace="LeaseFlow/SyntheticChecks",
        MetricData=[
            {
                "MetricName": "HealthCheckSuccess",
                "Dimensions": [
                    {"Name": "Environment", "Value": os.environ["ENVIRONMENT"]}
                ],
                "Value": 1.0 if success else 0.0,
                "Unit": "Count",
            }
        ],
    )

    if not success:
        raise RuntimeError(
            f"Synthetic health check failed — health={health_ok} props={props_ok}"
        )

    return {"health_ok": True, "props_ok": True}


def _http_get(url: str, headers: dict | None = None) -> bool:
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False
