"""
Management command to seed workflow templates
Creates sample workflows from templates for demonstration
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from workflows.templates import workflow_template_manager
from workflows.models import Workflow

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed workflow templates for all tenants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to seed (default: all tenants)',
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Specific template to create (default: all templates)',
        )
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of user to assign as workflow creator (default: first admin)',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing workflows with same name',
        )

    def handle(self, *args, **options):
        # Get target tenants
        if options['tenant']:
            try:
                tenants = [Tenant.objects.get(schema_name=options['tenant'])]
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant "{options["tenant"]}" does not exist.')
        else:
            tenants = Tenant.objects.all()

        # Get templates to create
        if options['template']:
            available_templates = workflow_template_manager.get_available_templates()
            template_ids = [t['id'] for t in available_templates]
            if options['template'] not in template_ids:
                raise CommandError(f'Template "{options["template"]}" not found. Available: {", ".join(template_ids)}')
            templates_to_create = [options['template']]
        else:
            templates_to_create = [t['id'] for t in workflow_template_manager.get_available_templates()]

        total_created = 0
        total_skipped = 0

        for tenant in tenants:
            self.stdout.write(f'\n📊 Processing tenant: {tenant.schema_name}')
            
            with schema_context(tenant.schema_name):
                # Get user to assign as creator
                if options['user_email']:
                    try:
                        creator = User.objects.get(email=options['user_email'])
                    except User.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'User with email {options["user_email"]} not found in {tenant.schema_name}. Skipping.')
                        )
                        continue
                else:
                    # Use first superuser or admin
                    creator = User.objects.filter(is_superuser=True).first()
                    if not creator:
                        creator = User.objects.filter(is_staff=True).first()
                    if not creator:
                        self.stdout.write(
                            self.style.WARNING(f'No admin user found in {tenant.schema_name}. Skipping.')
                        )
                        continue

                tenant_created = 0
                tenant_skipped = 0

                for template_id in templates_to_create:
                    try:
                        # Get template metadata
                        template_info = next(
                            (t for t in workflow_template_manager.get_available_templates() if t['id'] == template_id), 
                            None
                        )
                        
                        if not template_info:
                            self.stdout.write(
                                self.style.WARNING(f'Template {template_id} not found')
                            )
                            continue

                        workflow_name = template_info['name']
                        
                        # Check if workflow already exists
                        existing_workflow = Workflow.objects.filter(name=workflow_name).first()
                        if existing_workflow and not options['overwrite']:
                            self.stdout.write(f'  ⏭️  Skipping "{workflow_name}" (already exists)')
                            tenant_skipped += 1
                            continue
                        elif existing_workflow and options['overwrite']:
                            existing_workflow.delete()
                            self.stdout.write(f'  🔄 Overwriting "{workflow_name}"')

                        # Create workflow from template
                        workflow = workflow_template_manager.create_workflow_from_template(
                            template_id=template_id,
                            name=workflow_name,
                            description=template_info['description'],
                            created_by=creator
                        )

                        self.stdout.write(f'  ✅ Created "{workflow_name}" (ID: {workflow.id})')
                        tenant_created += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ❌ Failed to create "{template_id}": {str(e)}')
                        )
                        continue

                self.stdout.write(f'  📈 Tenant summary: {tenant_created} created, {tenant_skipped} skipped')
                total_created += tenant_created
                total_skipped += tenant_skipped

        # Final summary
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Workflow template seeding complete!')
        )
        self.stdout.write(f'📊 Total workflows created: {total_created}')
        self.stdout.write(f'📊 Total workflows skipped: {total_skipped}')
        self.stdout.write(f'📊 Tenants processed: {len(tenants)}')

        if total_created > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n🚀 You can now access these workflows in the Django admin or via API!')
            )
            self.stdout.write('💡 Next steps:')
            self.stdout.write('   1. Customize the workflows for your specific use cases')
            self.stdout.write('   2. Configure pipeline IDs and user assignments')
            self.stdout.write('   3. Set up triggers and test the workflows')
            self.stdout.write('   4. Activate workflows when ready for production')