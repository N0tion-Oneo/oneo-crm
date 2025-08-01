"""
Management command to seed the content management system with initial content
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from workflows.content.models import (
    ContentLibrary, ContentAsset, ContentTag, ContentType, 
    ContentStatus, ContentVisibility
)
from workflows.content.manager import content_manager

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the content management system with initial libraries, assets, and templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@example.com',
            help='Email of the admin user to create content as',
        )
    
    def handle(self, *args, **options):
        admin_email = options['admin_email']
        
        try:
            admin_user = User.objects.get(email=admin_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Admin user with email {admin_email} not found')
            )
            return
        
        self.stdout.write('Starting content library seeding...')
        
        # Create content libraries
        self.create_libraries(admin_user)
        
        # Create content tags
        self.create_tags(admin_user)
        
        # Create sample content assets
        self.create_sample_content(admin_user)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded content management system!')
        )
    
    def create_libraries(self, admin_user):
        """Create initial content libraries"""
        
        libraries_data = [
            {
                'name': 'Email Templates',
                'description': 'Reusable email templates for various communication scenarios',
                'visibility': ContentVisibility.ORGANIZATION,
                'requires_approval': True
            },
            {
                'name': 'Message Templates',
                'description': 'SMS, WhatsApp, and other messaging templates',
                'visibility': ContentVisibility.ORGANIZATION,
                'requires_approval': False
            },
            {
                'name': 'Brand Assets',
                'description': 'Company logos, images, and brand materials',
                'visibility': ContentVisibility.ORGANIZATION,
                'requires_approval': True
            },
            {
                'name': 'Document Templates',
                'description': 'Contract templates, proposals, and other document templates',
                'visibility': ContentVisibility.ORGANIZATION,
                'requires_approval': True
            },
            {
                'name': 'HTML Snippets',
                'description': 'Reusable HTML components and snippets',
                'visibility': ContentVisibility.ORGANIZATION,
                'requires_approval': False
            }
        ]
        
        for lib_data in libraries_data:
            library, created = ContentLibrary.objects.get_or_create(
                name=lib_data['name'],
                defaults={
                    'description': lib_data['description'],
                    'visibility': lib_data['visibility'],
                    'requires_approval': lib_data['requires_approval'],
                    'created_by': admin_user
                }
            )
            
            if created:
                self.stdout.write(f'  Created library: {library.name}')
            else:
                self.stdout.write(f'  Library already exists: {library.name}')
    
    def create_tags(self, admin_user):
        """Create initial content tags"""
        
        tags_data = [
            {'name': 'welcome', 'description': 'Welcome and onboarding content', 'category': 'onboarding', 'color_code': '#4CAF50'},
            {'name': 'follow-up', 'description': 'Follow-up and nurture content', 'category': 'engagement', 'color_code': '#2196F3'},
            {'name': 'promotional', 'description': 'Promotional and marketing content', 'category': 'marketing', 'color_code': '#FF9800'},
            {'name': 'transactional', 'description': 'Transaction and order related content', 'category': 'commerce', 'color_code': '#9C27B0'},
            {'name': 'support', 'description': 'Customer support content', 'category': 'support', 'color_code': '#F44336'},
            {'name': 'newsletter', 'description': 'Newsletter and update content', 'category': 'communication', 'color_code': '#607D8B'},
            {'name': 'urgent', 'description': 'Urgent and time-sensitive content', 'category': 'priority', 'color_code': '#FF5722'},
            {'name': 'personalized', 'description': 'Highly personalized content', 'category': 'customization', 'color_code': '#E91E63'}
        ]
        
        for tag_data in tags_data:
            tag, created = ContentTag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'description': tag_data['description'],
                    'category': tag_data['category'],
                    'color_code': tag_data['color_code'],
                    'created_by': admin_user
                }
            )
            
            if created:
                self.stdout.write(f'  Created tag: {tag.name}')
    
    def create_sample_content(self, admin_user):
        """Create sample content assets"""
        
        # Get libraries
        email_lib = ContentLibrary.objects.get(name='Email Templates')
        message_lib = ContentLibrary.objects.get(name='Message Templates')
        html_lib = ContentLibrary.objects.get(name='HTML Snippets')
        
        # Sample email templates
        email_templates = [
            {
                'name': 'Welcome Email',
                'content': '''Hello {{first_name}},

Welcome to {{company_name}}! We're thrilled to have you join our community.

Here's what you can expect:
• {{benefit_1}}
• {{benefit_2}}
• {{benefit_3}}

If you have any questions, don't hesitate to reach out to our support team.

Best regards,
{{sender_name}}
{{company_name}}''',
                'variables': ['first_name', 'company_name', 'benefit_1', 'benefit_2', 'benefit_3', 'sender_name'],
                'tags': ['welcome', 'onboarding']
            },
            {
                'name': 'Follow-up Email Template',
                'content': '''Hi {{first_name}},

I wanted to follow up on our conversation about {{topic}}.

{{follow_up_message}}

Would you be available for a quick call {{suggested_time}}?

Looking forward to hearing from you.

Best,
{{sender_name}}''',
                'variables': ['first_name', 'topic', 'follow_up_message', 'suggested_time', 'sender_name'],
                'tags': ['follow-up', 'personalized']
            },
            {
                'name': 'Newsletter Template',
                'content': '''{{newsletter_title}}

Dear {{first_name}},

Here are this week's highlights:

{{content_section_1}}

{{content_section_2}}

{{content_section_3}}

Thanks for reading!

The {{company_name}} Team

Unsubscribe: {{unsubscribe_link}}''',
                'variables': ['newsletter_title', 'first_name', 'content_section_1', 'content_section_2', 'content_section_3', 'company_name', 'unsubscribe_link'],
                'tags': ['newsletter', 'communication']
            }
        ]
        
        for template_data in email_templates:
            asset = content_manager.create_text_content(
                name=template_data['name'],
                content_type=ContentType.EMAIL_TEMPLATE,
                content_text=template_data['content'],
                library=email_lib,
                created_by=admin_user,
                template_variables=template_data['variables'],
                tags=template_data['tags'],
                visibility=ContentVisibility.ORGANIZATION
            )
            self.stdout.write(f'  Created email template: {asset.name}')
        
        # Sample message templates
        message_templates = [
            {
                'name': 'SMS Welcome',
                'content': 'Hi {{first_name}}! Welcome to {{company_name}}. Your account is now active. Reply STOP to opt out.',
                'variables': ['first_name', 'company_name'],
                'tags': ['welcome', 'transactional']
            },
            {
                'name': 'WhatsApp Follow-up',
                'content': '''Hello {{first_name}}! 👋

Thanks for your interest in {{product_name}}. 

{{follow_up_message}}

Any questions? Just reply to this message!''',
                'variables': ['first_name', 'product_name', 'follow_up_message'],
                'tags': ['follow-up', 'personalized']
            }
        ]
        
        for template_data in message_templates:
            asset = content_manager.create_text_content(
                name=template_data['name'],
                content_type=ContentType.MESSAGE_TEMPLATE,
                content_text=template_data['content'],
                library=message_lib,
                created_by=admin_user,
                template_variables=template_data['variables'],
                tags=template_data['tags'],
                visibility=ContentVisibility.ORGANIZATION
            )
            self.stdout.write(f'  Created message template: {asset.name}')
        
        # Sample HTML snippets
        html_snippets = [
            {
                'name': 'Email Header',
                'content': '''<div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
    <img src="{{logo_url}}" alt="{{company_name}}" style="max-height: 60px;">
    <h1 style="color: #333; margin: 10px 0;">{{company_name}}</h1>
</div>''',
                'variables': ['logo_url', 'company_name'],
                'tags': ['email', 'branding']
            },
            {
                'name': 'Email Footer',
                'content': '''<div style="background-color: #333; color: #fff; padding: 20px; text-align: center; font-size: 12px;">
    <p>{{company_name}} | {{company_address}}</p>
    <p>
        <a href="{{website_url}}" style="color: #fff;">Website</a> | 
        <a href="{{unsubscribe_url}}" style="color: #fff;">Unsubscribe</a>
    </p>
</div>''',
                'variables': ['company_name', 'company_address', 'website_url', 'unsubscribe_url'],
                'tags': ['email', 'footer']
            }
        ]
        
        for snippet_data in html_snippets:
            asset = content_manager.create_text_content(
                name=snippet_data['name'],
                content_type=ContentType.HTML_SNIPPET,
                content_text=snippet_data['content'],
                library=html_lib,
                created_by=admin_user,
                template_variables=snippet_data['variables'],
                tags=snippet_data['tags'],
                visibility=ContentVisibility.ORGANIZATION
            )
            self.stdout.write(f'  Created HTML snippet: {asset.name}')
        
        self.stdout.write('Sample content creation completed!')