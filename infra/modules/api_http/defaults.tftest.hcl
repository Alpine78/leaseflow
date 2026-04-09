mock_provider "aws" {}

variables {
  name_prefix                 = "leaseflow-dev"
  aws_region                  = "eu-north-1"
  stage_name                  = "dev"
  lambda_invoke_arn           = "arn:aws:lambda:eu-north-1:123456789012:function:leaseflow-dev-backend:$LATEST"
  lambda_function_name        = "leaseflow-dev-backend"
  cognito_user_pool_id        = "eu-north-1_example"
  cognito_user_pool_client_id = "exampleclientid"
  tags = {
    Project = "leaseflow"
  }
}

run "exposes_backend_route_parity" {
  command = plan

  assert {
    condition     = aws_apigatewayv2_route.list_leases.route_key == "GET /leases"
    error_message = "API module should expose GET /leases."
  }

  assert {
    condition     = aws_apigatewayv2_route.create_lease.route_key == "POST /leases"
    error_message = "API module should expose POST /leases."
  }

  assert {
    condition     = aws_apigatewayv2_route.list_notifications.route_key == "GET /notifications"
    error_message = "API module should expose GET /notifications."
  }

  assert {
    condition     = aws_apigatewayv2_route.mark_notification_read.route_key == "PATCH /notifications/{notification_id}/read"
    error_message = "API module should expose PATCH /notifications/{notification_id}/read."
  }

  assert {
    condition     = aws_apigatewayv2_route.list_due_lease_reminders.route_key == "GET /lease-reminders/due-soon"
    error_message = "API module should expose GET /lease-reminders/due-soon."
  }

  assert {
    condition     = aws_apigatewayv2_route.list_leases.authorization_type == "JWT"
    error_message = "New tenant-facing routes should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.list_notifications.authorization_type == "JWT"
    error_message = "Notification route should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.mark_notification_read.authorization_type == "JWT"
    error_message = "Notification read route should require JWT auth."
  }
}
