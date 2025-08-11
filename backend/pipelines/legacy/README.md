# Legacy Pipeline Files

🔴 **WARNING: These files are deprecated and should not be used in new code.**

This directory contains legacy validation and migration files that have been replaced by the unified validation system in `pipelines/validation/`.

## Files in this directory:

### Validation System Files (Deprecated 2025-01-10 → 2025-08-10)

- **`validators_old.py`**
  - **Replaced by:** `pipelines/validation/data_validator.py`
  - **Description:** Old field validation system
  - **Use instead:** `from pipelines.validation import FieldValidator, validate_record_data`

- **`migration_validator_old.py`**
  - **Replaced by:** `pipelines/validation/migration_validator.py`
  - **Description:** Old migration validation with hard-denial rules
  - **Use instead:** `from pipelines.validation import MigrationValidator`

- **`migrator_old.py`**
  - **Replaced by:** `pipelines/validation/data_migrator.py`
  - **Description:** Old field schema migration engine
  - **Use instead:** `from pipelines.validation import DataMigrator, MigrationResult`

- **`data_migrator_old.py`**
  - **Replaced by:** `pipelines/validation/data_migrator.py`
  - **Description:** Old unified data migration engine
  - **Use instead:** `from pipelines.validation import DataMigrator, MigrationResult`

### Signal System Files (Deprecated 2025-08-10)

- **`signals_refactored.py`**
  - **Replaced by:** `pipelines/signals.py`
  - **Description:** Alternative signal implementation that was never activated
  - **Use instead:** Current system uses `pipelines/signals.py` (imported in apps.py)

## Migration Status

✅ **All legacy files have been successfully replaced by the unified validation system.**

### Active Unified System Location: `pipelines/validation/`

- `field_validator.py` - Unified field validation (replaces multiple old files)
- `data_validator.py` - Field data validation
- `migration_validator.py` - Migration safety validation  
- `data_migrator.py` - Data migration engine

### Integration Complete:

- ✅ All model validation methods now delegate to unified system
- ✅ Backward compatibility maintained
- ✅ No breaking changes to existing API
- ✅ All tests passing
- ✅ Production deployment ready

## Important Notes:

1. **Do not import from this directory** - All functionality has been moved to `pipelines/validation/`
2. **These files are kept for reference only** - They may be removed in future versions
3. **All new code should use the unified system** - See `pipelines/validation/` for current implementations

## Date Moved to Legacy:
**August 10, 2025** - Part of validation system consolidation project