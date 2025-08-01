"""
Celery tasks for pipeline-related async processing
"""

from celery import shared_task
from django.core.cache import cache
import logging
import json

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='pipelines.tasks.process_ai_field')
def process_ai_field(self, record_id, field_id, prompt, context_data=None):
    """
    Process AI field calculations asynchronously
    Used for: AI-powered field processing, content generation, analysis
    """
    try:
        from .models import Record, Field
        from .ai_processor import AIFieldProcessor
        
        record = Record.objects.get(id=record_id)
        field = Field.objects.get(id=field_id)
        
        # Process AI field
        processor = AIFieldProcessor()
        result = processor.process_field(
            field=field,
            record=record,
            prompt=prompt,
            context=context_data or {}
        )
        
        # Update record with AI result
        if result.get('success'):
            record_data = record.data.copy()
            record_data[field.name] = result['value']
            record.data = record_data
            record.save()
        
        # Cache the result for streaming responses
        cache_key = f"ai_field_result:{self.request.id}"
        cache.set(cache_key, result, timeout=3600)
        
        logger.info(f"AI field processed for record {record_id}, field {field_id}")
        return result
        
    except Exception as e:
        error_msg = f"AI field processing error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.process_bulk_operation')
def process_bulk_operation(self, operation_type, record_ids, operation_data):
    """
    Process bulk operations on multiple records
    Used for: Bulk updates, mass data imports, batch processing
    """
    try:
        from .models import Record
        
        records = Record.objects.filter(id__in=record_ids)
        processed_count = 0
        errors = []
        
        for record in records:
            try:
                if operation_type == 'update':
                    # Bulk update operation
                    record_data = record.data.copy()
                    record_data.update(operation_data.get('updates', {}))
                    record.data = record_data
                    record.save()
                    
                elif operation_type == 'delete':
                    # Bulk delete operation
                    record.delete()
                    
                elif operation_type == 'export':
                    # Export operation would generate files
                    pass
                    
                processed_count += 1
                
            except Exception as record_error:
                errors.append({
                    'record_id': record.id,
                    'error': str(record_error)
                })
        
        result = {
            'operation_type': operation_type,
            'processed_count': processed_count,
            'total_records': len(record_ids),
            'errors': errors,
            'success': len(errors) == 0
        }
        
        # Cache result for status checking
        cache_key = f"bulk_operation:{self.request.id}"
        cache.set(cache_key, result, timeout=3600)
        
        logger.info(f"Bulk operation {operation_type} processed {processed_count} records")
        return result
        
    except Exception as e:
        error_msg = f"Bulk operation error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}


@shared_task(bind=True, name='pipelines.tasks.generate_pipeline_report')
def generate_pipeline_report(self, pipeline_id, report_type, filters=None):
    """
    Generate comprehensive pipeline reports
    Used for: Analytics, data exports, performance reports
    """
    try:
        from .models import Pipeline, Record
        
        pipeline = Pipeline.objects.get(id=pipeline_id)
        records = Record.objects.filter(pipeline=pipeline)
        
        # Apply filters if provided
        if filters:
            # Add filtering logic here
            pass
        
        # Generate report based on type
        if report_type == 'summary':
            report_data = {
                'pipeline_name': pipeline.name,
                'total_records': records.count(),
                'field_distribution': {},
                'recent_activity': []
            }
        elif report_type == 'detailed':
            report_data = {
                'pipeline_name': pipeline.name,
                'records': [record.data for record in records[:1000]],  # Limit for performance
                'field_definitions': [field.to_dict() for field in pipeline.fields.all()]
            }
        
        # Cache the report
        cache_key = f"pipeline_report:{self.request.id}"
        cache.set(cache_key, report_data, timeout=7200)  # 2 hours
        
        logger.info(f"Report generated for pipeline {pipeline_id}")
        return {
            'report_type': report_type,
            'pipeline_id': pipeline_id,
            'status': 'completed',
            'cache_key': cache_key
        }
        
    except Exception as e:
        error_msg = f"Report generation error: {e}"
        logger.error(error_msg)
        return {'error': error_msg, 'success': False}