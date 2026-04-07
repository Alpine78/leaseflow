output "schedule_arn" {
  value       = aws_scheduler_schedule.this.arn
  description = "ARN of the reminder scan schedule."
}

output "schedule_name" {
  value       = aws_scheduler_schedule.this.name
  description = "Name of the reminder scan schedule."
}
