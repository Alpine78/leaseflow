# SES API Integration Path Evaluation

## Purpose

This document evaluates whether the current SES SMTP over PrivateLink delivery
path should be replaced or supplemented with SES API v2 (HTTP/SDK) for
production delivery. The evaluation covers cost, operational tradeoffs, and
security considerations for the three realistic paths available given the current
network architecture.

This is a planning evaluation only. No implementation, Terraform, or code change
is part of this document.

Related planning document: `docs/ses-production-delivery-hardening.md`

## Current State

- The notification delivery worker sends email via SES SMTP.
- The Lambda backend runs in private subnets with no NAT Gateway.
- SMTP traffic reaches SES through a VPC interface endpoint:
  `com.amazonaws.eu-north-1.email-smtp`.
- SMTP credentials are operator-created outside Terraform and stored in SSM
  SecureString parameters.
- The `smtplib` standard library handles the SMTP connection in the worker.
- The VPC endpoint is disabled by default (`ses_smtp_vpc_endpoint_enabled = false`)
  to avoid idle cost in dev.

## Delivery Paths Evaluated

| Path | Description | VPC dependency | Auth |
|------|-------------|----------------|------|
| A | SES SMTP over interface VPC endpoint (current) | Interface endpoint `email-smtp` | SMTP credentials in SSM SecureString |
| B | SES API v2 via NAT Gateway | NAT Gateway in private subnets | Lambda IAM execution role |
| C | SES API v2 via VPC interface endpoint | Not available | — |

Path C is not a valid option. AWS does not offer a VPC interface endpoint for
SES API v2. VPC gateway endpoints exist only for S3 and DynamoDB. Any SES API
call from a Lambda in private subnets requires internet access through a NAT
Gateway or a transit path outside the current VPC design.

## Cost Comparison

Pricing for `eu-north-1` as of evaluation date. All figures are idle baselines
— no email send volume assumed.

### Path A — SES SMTP Interface Endpoint

| Component | Unit cost | 2-AZ production monthly |
|-----------|-----------|------------------------|
| Interface endpoint (per AZ) | $0.013/hr | $0.013 × 2 × 730 ≈ **$19.00** |
| Data processed | $0.01/GB | variable, low for notification mail |

Total idle: **~$19/month** across two AZs.

The endpoint can be disabled when production delivery is paused to eliminate the
idle charge entirely.

### Path B — SES API v2 via NAT Gateway

| Component | Unit cost | Single-AZ monthly |
|-----------|-----------|-------------------|
| NAT Gateway idle | $0.043/hr | $0.043 × 730 ≈ **$31.39** |
| Data processed | $0.043/GB | variable |

Total idle: **~$31/month** for a single-AZ NAT Gateway. A production 2-AZ NAT
configuration costs ~$63/month idle.

A single-AZ NAT Gateway costs approximately 65% more than the 2-AZ SMTP
endpoint at idle. Unlike the SMTP endpoint, NAT Gateway cannot be cleanly
disabled between delivery windows without removing and recreating the resource.

## Operational Differences

### Credential Management

- **Path A**: SMTP credentials are IAM-derived but exported as long-lived
  username/password pairs. The operator creates them manually, stores them in SSM
  SecureString parameters, and is responsible for rotation. The credentials have
  no resource-level scope and grant SMTP sending access broadly.
- **Path B**: No separate credentials. The Lambda execution IAM role is granted
  `ses:SendEmail` with an optional resource-level condition on the configuration
  set or sending identity. Credentials rotate automatically with AWS. No SSM
  parameters for credentials.

### SDK And Error Handling

- **Path A**: Uses Python `smtplib` (standard library) with a hand-written retry
  loop. SMTP error codes are protocol-level strings that require mapping to
  application error categories. The worker implements its own attempt counting
  and failure classification.
- **Path B**: Uses `boto3` (`ses_v2` client), already a Lambda dependency.
  `boto3` provides structured Python exceptions, built-in retry configuration,
  and direct access to error codes like `MessageRejected`,
  `MailFromDomainNotVerified`, and `SendingPausedException`. Error mapping is
  cleaner and more maintainable.

### Connection Overhead

- **Path A**: Each Lambda invocation establishes a new SMTP TCP+TLS connection.
  Lambda does not maintain a warm SMTP connection pool across cold starts. The
  TLS handshake adds measurable latency for small batches.
- **Path B**: `boto3` uses HTTPS with connection pooling scoped to the Lambda
  execution environment. Warm Lambda instances may reuse connections, reducing
  per-message overhead.

### Idempotency

- **Path A**: SMTP has no idempotency primitive. The current worker prevents
  duplicate sends by checking `sent_at` in the delivery table before attempting
  a send, but if Lambda crashes after SES accepts the message and before the DB
  status write commits, the message may have been delivered without a `sent_at`
  record.
- **Path B**: SES API v2 `SendEmail` accepts a `ClientToken` parameter that
  provides idempotency at the SES API level for a short window. This does not
  fully eliminate the at-least-once delivery risk on crash, but it adds a second
  layer of deduplication.

### Bounce And Complaint Feedback

Both paths integrate with SES configuration sets and EventBridge event
destinations in the same way. The feedback ingestion path is independent of
the send path. This dimension is equal across A and B.

## Security Considerations

### Path A

- SMTP credentials are long-lived and require manual rotation.
- Credentials are stored in SSM SecureString with KMS encryption — operator
  access is audited through CloudTrail.
- The VPC interface endpoint keeps all SMTP traffic within the AWS private
  network. No internet egress for email delivery.
- The endpoint security group restricts ingress to port 587 from the Lambda
  security group only.

### Path B

- No long-lived credential material. IAM role assumption is bounded to the
  Lambda execution lifetime.
- The IAM grant can be scoped to a specific SES sending identity and
  configuration set, limiting the blast radius of a compromised execution role.
- NAT Gateway introduces a general internet egress path from the private subnets.
  Once a NAT Gateway exists, any Lambda (or code running in Lambda) can reach
  arbitrary internet endpoints — this is a broader change to the network security
  posture, not limited to email traffic.
- The NAT Gateway security model relies on security groups and NACLs to restrict
  outbound traffic, which requires explicit hardening to avoid becoming a general
  internet egress path.

Both paths keep RDS private. Neither path requires browser-triggerable delivery
or exposes the delivery worker through an API Gateway route.

## Recommendation

**Retain Path A (SES SMTP over PrivateLink) as the production path.**

The cost and network security tradeoffs do not justify adding a NAT Gateway
solely to reach SES API:

1. NAT Gateway idle cost ($31–63/month depending on AZ count) exceeds the SMTP
   endpoint cost (~$19/month for 2 AZs) before a single message is sent.
2. There is no VPC endpoint for SES API v2, so Path B unavoidably requires NAT
   Gateway.
3. NAT Gateway introduces a general internet egress path from private subnets,
   which conflicts with the current private networking posture.
4. The operational advantages of Path B — IAM auth, `boto3` SDK, idempotency
   tokens — are real but do not outweigh the cost and network posture
   disadvantages under current constraints.

The SMTP endpoint remains the cost-optimal, network-private production path for
a Lambda in private subnets with no NAT Gateway.

## Conditions Under Which This Decision Should Be Revisited

- **NAT Gateway added for other services**: If a NAT Gateway enters the VPC for
  an unrelated reason, the marginal cost of switching to SES API v2 drops to
  near zero. At that point, Path B's operational advantages (IAM auth, `boto3`,
  idempotency tokens, no credential rotation) make it the preferred forward path.
- **Lambda moved outside the VPC**: If the backend Lambda is redesigned to run
  outside a VPC (e.g., to simplify networking or reduce cold-start latency), SES
  API v2 is the natural choice with no infrastructure dependency.
- **SMTP credential rotation compliance requirement**: If a compliance framework
  requires short-lived credential rotation, Path B's IAM model eliminates the
  requirement entirely.
- **Pricing changes**: AWS regularly updates VPC endpoint and NAT Gateway
  pricing. Re-evaluate if the cost delta narrows significantly.

## References

- [Amazon SES VPC endpoints](https://docs.aws.amazon.com/ses/latest/dg/send-email-set-up-vpc-endpoints.html)
- [Amazon SES SMTP interface](https://docs.aws.amazon.com/ses/latest/dg/send-email-smtp.html)
- [Amazon SES API v2 SendEmail](https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_SendEmail.html)
- [Amazon SES pricing](https://aws.amazon.com/ses/pricing/)
- [AWS VPC interface endpoint pricing](https://aws.amazon.com/privatelink/pricing/)
- [AWS NAT Gateway pricing](https://aws.amazon.com/vpc/pricing/)
- [boto3 SES v2 client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sesv2.html)
- [AWS VPC Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)
