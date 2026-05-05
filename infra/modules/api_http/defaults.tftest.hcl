mock_provider "aws" {}

variables {
  name_prefix                 = "leaseflow-dev"
  aws_region                  = "eu-north-1"
  cors_allow_credentials      = false
  cors_allow_headers          = ["Authorization", "Content-Type"]
  cors_allow_methods          = ["GET", "OPTIONS", "PATCH", "POST"]
  cors_allowed_origins        = ["http://localhost:5173"]
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
    condition     = aws_apigatewayv2_route.update_lease.route_key == "PATCH /leases/{lease_id}"
    error_message = "API module should expose PATCH /leases/{lease_id}."
  }

  assert {
    condition     = aws_apigatewayv2_route.list_notifications.route_key == "GET /notifications"
    error_message = "API module should expose GET /notifications."
  }

  assert {
    condition     = aws_apigatewayv2_route.list_notification_contacts.route_key == "GET /notification-contacts"
    error_message = "API module should expose GET /notification-contacts."
  }

  assert {
    condition     = aws_apigatewayv2_route.create_notification_contact.route_key == "POST /notification-contacts"
    error_message = "API module should expose POST /notification-contacts."
  }

  assert {
    condition     = aws_apigatewayv2_route.update_notification_contact.route_key == "PATCH /notification-contacts/{contact_id}"
    error_message = "API module should expose PATCH /notification-contacts/{contact_id}."
  }

  assert {
    condition     = aws_apigatewayv2_route.mark_notification_read.route_key == "PATCH /notifications/{notification_id}/read"
    error_message = "API module should expose PATCH /notifications/{notification_id}/read."
  }

  assert {
    condition     = aws_apigatewayv2_route.update_property.route_key == "PATCH /properties/{property_id}"
    error_message = "API module should expose PATCH /properties/{property_id}."
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
    condition     = aws_apigatewayv2_route.list_notification_contacts.authorization_type == "JWT"
    error_message = "Notification contact list route should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.create_notification_contact.authorization_type == "JWT"
    error_message = "Notification contact create route should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.update_notification_contact.authorization_type == "JWT"
    error_message = "Notification contact update route should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.update_lease.authorization_type == "JWT"
    error_message = "Lease update route should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.mark_notification_read.authorization_type == "JWT"
    error_message = "Notification read route should require JWT auth."
  }

  assert {
    condition     = aws_apigatewayv2_route.update_property.authorization_type == "JWT"
    error_message = "Property update route should require JWT auth."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_origins, "http://localhost:5173"), false)
    error_message = "HTTP API should allow the local frontend origin by default."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_headers, "Authorization"), false)
    error_message = "HTTP API should allow the Authorization header for browser calls."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_headers, "Content-Type"), false)
    error_message = "HTTP API should allow the Content-Type header for browser calls."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_methods, "GET"), false)
    error_message = "HTTP API should allow GET in browser CORS."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_methods, "POST"), false)
    error_message = "HTTP API should allow POST in browser CORS."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_methods, "PATCH"), false)
    error_message = "HTTP API should allow PATCH in browser CORS."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_methods, "OPTIONS"), false)
    error_message = "HTTP API should allow OPTIONS in browser CORS."
  }

  assert {
    condition     = aws_apigatewayv2_api.this.cors_configuration[0].allow_credentials == false
    error_message = "HTTP API should not allow browser credentials for this frontend phase."
  }
}

run "supports_optional_hosted_frontend_origin" {
  command = plan

  variables {
    cors_allowed_origins = [
      "http://localhost:5173",
      "https://demo.example.com",
    ]
  }

  assert {
    condition     = try(length(aws_apigatewayv2_api.this.cors_configuration[0].allow_origins), 0) == 2
    error_message = "HTTP API should allow both the local and hosted frontend origins when configured."
  }

  assert {
    condition     = try(contains(aws_apigatewayv2_api.this.cors_configuration[0].allow_origins, "https://demo.example.com"), false)
    error_message = "HTTP API should include the configured hosted frontend origin."
  }
}
