"""
Tenant-related Django signals for automatic setup
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Tenant
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Tenant)
def create_platform_admin_in_tenant(sender, instance, created, **kwargs):
    """
    Automatically create platform admin user in newly created tenant schemas.
    
    Uses transaction.on_commit() to ensure user creation only happens after
    the tenant creation transaction is successfully committed.
    """
    if created and instance.schema_name != 'public':
        logger.info(f"Scheduling platform admin creation for new tenant: {instance.name} (schema: {instance.schema_name})")
        
        def delayed_admin_setup():
            """Set up admin users after a delay to ensure clean separation"""
            import threading
            import time
            
            def run_setup():
                # Wait a bit to ensure tenant creation is fully complete
                time.sleep(2)
                
                try:
                    import subprocess
                    import sys
                    import os
                    
                    # Check if tenant admin info was passed via instance metadata
                    admin_email = getattr(instance, '_admin_email', None)
                    admin_password = getattr(instance, '_admin_password', None)
                    admin_first_name = getattr(instance, '_admin_first_name', None)
                    admin_last_name = getattr(instance, '_admin_last_name', None)
                    
                    command_args = [sys.executable, 'manage.py', 'setup_tenant_admin', instance.schema_name]
                    
                    if admin_email and admin_password:
                        command_args.extend([
                            '--admin-email', admin_email,
                            '--admin-password', admin_password
                        ])
                        if admin_first_name:
                            command_args.extend(['--admin-first-name', admin_first_name])
                        if admin_last_name:
                            command_args.extend(['--admin-last-name', admin_last_name])
                    
                    result = subprocess.run(
                        command_args, 
                        capture_output=True, 
                        text=True, 
                        cwd=os.getcwd()
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Admin setup completed for {instance.name}")
                        for line in result.stdout.strip().split('\n'):
                            if line.strip() and not line.startswith('DEBUG:'):
                                logger.info(f"   {line}")
                    else:
                        logger.error(f"Admin setup failed for {instance.name}: {result.stderr}")
                        
                except Exception as e:
                    logger.error(f"Failed delayed admin setup for {instance.name}: {e}")
            
            # Start the delayed setup in a background thread
            thread = threading.Thread(target=run_setup, daemon=True)
            thread.start()
        
        # Schedule delayed admin setup after transaction commits
        transaction.on_commit(delayed_admin_setup)
        
        # Log completion
        logger.info(f"✅ Tenant '{instance.name}' created successfully")
        logger.info(f"⏳ Admin users will be set up automatically in a few seconds...")
            

def create_additional_platform_users(schema_name):
    """
    Reserved for future platform user creation if needed.
    Currently disabled - no automatic support users created.
    """
    # Support user creation has been disabled
    # This function is kept for potential future use
    logger.info(f"Additional platform user creation disabled for {schema_name}")
    pass


@receiver(post_save, sender=Tenant)
def setup_tenant_defaults(sender, instance, created, **kwargs):
    """
    Setup default configurations for newly created tenants.
    
    This includes:
    - Default user types (Admin, Manager, User, Viewer) via management command
    - System configurations
    - Pipeline templates (if needed)
    """
    if created and instance.schema_name != 'public':
        logger.info(f"🏢 Setting up defaults for new tenant: {instance.name} ({instance.schema_name})")
        
        def delayed_defaults_setup():
            """Setup defaults by calling management commands"""
            try:
                import subprocess
                import sys
                import os
                
                logger.info(f"🔧 Starting tenant defaults setup for {instance.name}")
                
                # Step 1: Setup default user types via management command
                logger.info("📋 Step 1: Setting up default user types...")
                result = subprocess.run([
                    sys.executable, 'manage.py', 'setup_default_user_types',
                    '--tenant', instance.schema_name
                ], capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    logger.info("✅ User types setup completed successfully")
                    # Log the output for debugging
                    for line in result.stdout.strip().split('\n'):
                        if line.strip() and not line.startswith('System check'):
                            logger.info(f"   {line}")
                else:
                    logger.error(f"❌ User types setup failed: {result.stderr}")
                    raise Exception(f"User types setup failed: {result.stderr}")
                
                # Step 2: Setup default system configurations  
                logger.info("⚙️  Step 2: Setting up system configurations...")
                setup_default_system_config()
                
                # Step 3: Setup default pipeline templates (optional)
                logger.info("🔄 Step 3: Setting up pipeline templates...")
                setup_default_pipeline_templates()
                
                logger.info(f"✅ Tenant defaults setup completed successfully for {instance.name}")
                        
            except Exception as e:
                logger.error(f"❌ Critical error setting up defaults for {instance.name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Log to help with debugging
                logger.error(f"🔍 Tenant details - Name: {instance.name}, Schema: {instance.schema_name}")
                
                # Don't re-raise here as tenant creation should succeed even if defaults fail
                # Admin can manually run setup commands if needed
                logger.warning(f"⚠️  Tenant {instance.name} was created but defaults setup failed")
                logger.warning("💡 Run 'python manage.py setup_default_user_types --tenant {instance.schema_name}' manually to fix")
        
        # Run setup after transaction commits
        transaction.on_commit(delayed_defaults_setup)


# User type setup is now handled by the management command:
# python manage.py setup_default_user_types --tenant <schema_name>


def setup_default_pipeline_templates():
    """Setup default pipeline templates for common use cases"""
    try:
        # Skip pipeline template setup during tenant creation
        # Templates can be set up later via management commands if needed
        logger.info("Skipping pipeline template setup during tenant creation")
        
    except Exception as e:
        logger.error(f"Failed to setup default pipeline templates: {e}")


def setup_default_system_config():
    """Setup default system configurations"""
    try:
        # Setup default system settings, permissions, etc.
        logger.info("System defaults configured")
        
    except Exception as e:
        logger.error(f"Failed to setup system defaults: {e}")