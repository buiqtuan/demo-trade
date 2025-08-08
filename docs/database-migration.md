# Database Migration for Authentication Updates

## Summary

This document outlines the database schema changes required for the new authentication system.

## Changes Made

### User Model Updates

The User model in `models.py` has been updated with new fields:

```python
# New fields added:
display_name = Column(String, nullable=True)
avatar_url = Column(String, nullable=True) 
updated_at = Column(DateTime(timezone=True), nullable=True)
```

### Required Database Migration

If you have an existing database, you'll need to run a migration to add these columns:

```sql
ALTER TABLE users ADD COLUMN display_name VARCHAR;
ALTER TABLE users ADD COLUMN avatar_url VARCHAR;
ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;
```

### For New Installations

For new installations, the `CREATE TABLE` statement will automatically include these fields when the application starts.

## Migration Commands

If using Alembic for migrations:

```bash
# Generate migration
alembic revision --autogenerate -m "Add display_name, avatar_url, updated_at to users"

# Apply migration
alembic upgrade head
```

## Default Values

- `display_name`: NULL (optional)
- `avatar_url`: NULL (optional)
- `updated_at`: NULL initially, updated when user profile is modified

## Backward Compatibility

The new fields are all nullable, so existing user records will continue to work without any data loss.
