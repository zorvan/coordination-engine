# Coordination Engine — Clean Architecture
#
# Layers (inner → outer):
#   domain       → Core business rules, entities, value objects, domain events
#   application  → Use cases, commands/queries, DTOs, application services
#   infrastructure → SQLAlchemy repos, Telegram API, LLM clients, schedulers
#   presentation → Telegram bot handlers, keyboards, message formatters
#   shared       → Config, logging, DI container, cross-cutting utilities
#
# Dependency rule: inner layers know NOTHING about outer layers.
# All dependencies flow inward through interfaces (ports).
