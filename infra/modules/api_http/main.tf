resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name_prefix}-http-api"
  protocol_type = "HTTP"
  tags          = merge(var.tags, { Name = "${var.name_prefix}-http-api" })

  cors_configuration {
    allow_credentials = var.cors_allow_credentials
    allow_headers     = var.cors_allow_headers
    allow_methods     = var.cors_allow_methods
    allow_origins     = var.cors_allowed_origins
  }
}

resource "aws_apigatewayv2_integration" "backend" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "${var.name_prefix}-jwt-authorizer"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [var.cognito_user_pool_client_id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.backend.id}"
}

resource "aws_apigatewayv2_route" "list_properties" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "GET /properties"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "create_property" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "POST /properties"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "update_property" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "PATCH /properties/{property_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "list_leases" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "GET /leases"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "create_lease" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "POST /leases"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "update_lease" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "PATCH /leases/{lease_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "list_notifications" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "GET /notifications"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "list_notification_contacts" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "GET /notification-contacts"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "create_notification_contact" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "POST /notification-contacts"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "update_notification_contact" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "PATCH /notification-contacts/{contact_id}"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "mark_notification_read" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "PATCH /notifications/{notification_id}/read"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "list_due_lease_reminders" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "GET /lease-reminders/due-soon"
  target             = "integrations/${aws_apigatewayv2_integration.backend.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.stage_name
  auto_deploy = true
  tags        = merge(var.tags, { Name = "${var.name_prefix}-${var.stage_name}" })
}

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
