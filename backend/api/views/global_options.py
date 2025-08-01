"""
API views for global configuration options
Provides currencies, countries, OpenAI models, and other dynamic reference data
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class GlobalOptionsViewSet(viewsets.GenericViewSet):
    """
    Read-only viewset for global configuration options
    Provides currencies, countries, OpenAI models, etc.
    """
    permission_classes = [IsAuthenticated]
    
    def get_currencies(self):
        """Get list of supported currencies"""
        return [
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
            {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$'},
            {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'A$'},
            {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'},
            {'code': 'CHF', 'name': 'Swiss Franc', 'symbol': 'CHF'},
            {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥'},
            {'code': 'INR', 'name': 'Indian Rupee', 'symbol': '₹'},
            {'code': 'KRW', 'name': 'South Korean Won', 'symbol': '₩'},
            {'code': 'SGD', 'name': 'Singapore Dollar', 'symbol': 'S$'},
            {'code': 'HKD', 'name': 'Hong Kong Dollar', 'symbol': 'HK$'},
            {'code': 'NOK', 'name': 'Norwegian Krone', 'symbol': 'kr'},
            {'code': 'SEK', 'name': 'Swedish Krona', 'symbol': 'kr'},
            {'code': 'DKK', 'name': 'Danish Krone', 'symbol': 'kr'},
            {'code': 'NZD', 'name': 'New Zealand Dollar', 'symbol': 'NZ$'},
            {'code': 'MXN', 'name': 'Mexican Peso', 'symbol': '$'},
            {'code': 'BRL', 'name': 'Brazilian Real', 'symbol': 'R$'},
            {'code': 'RUB', 'name': 'Russian Ruble', 'symbol': '₽'},
            {'code': 'ZAR', 'name': 'South African Rand', 'symbol': 'R'},
        ]
    
    def get_countries(self):
        """Get list of supported countries with phone codes"""
        return [
            {'code': 'US', 'name': 'United States', 'phone_code': '+1'},
            {'code': 'CA', 'name': 'Canada', 'phone_code': '+1'},
            {'code': 'GB', 'name': 'United Kingdom', 'phone_code': '+44'},
            {'code': 'DE', 'name': 'Germany', 'phone_code': '+49'},
            {'code': 'FR', 'name': 'France', 'phone_code': '+33'},
            {'code': 'IT', 'name': 'Italy', 'phone_code': '+39'},
            {'code': 'ES', 'name': 'Spain', 'phone_code': '+34'},
            {'code': 'NL', 'name': 'Netherlands', 'phone_code': '+31'},
            {'code': 'BE', 'name': 'Belgium', 'phone_code': '+32'},
            {'code': 'CH', 'name': 'Switzerland', 'phone_code': '+41'},
            {'code': 'AT', 'name': 'Austria', 'phone_code': '+43'},
            {'code': 'SE', 'name': 'Sweden', 'phone_code': '+46'},
            {'code': 'NO', 'name': 'Norway', 'phone_code': '+47'},
            {'code': 'DK', 'name': 'Denmark', 'phone_code': '+45'},
            {'code': 'FI', 'name': 'Finland', 'phone_code': '+358'},
            {'code': 'PL', 'name': 'Poland', 'phone_code': '+48'},
            {'code': 'CZ', 'name': 'Czech Republic', 'phone_code': '+420'},
            {'code': 'HU', 'name': 'Hungary', 'phone_code': '+36'},
            {'code': 'RO', 'name': 'Romania', 'phone_code': '+40'},
            {'code': 'BG', 'name': 'Bulgaria', 'phone_code': '+359'},
            {'code': 'HR', 'name': 'Croatia', 'phone_code': '+385'},
            {'code': 'SI', 'name': 'Slovenia', 'phone_code': '+386'},
            {'code': 'SK', 'name': 'Slovakia', 'phone_code': '+421'},
            {'code': 'LT', 'name': 'Lithuania', 'phone_code': '+370'},
            {'code': 'LV', 'name': 'Latvia', 'phone_code': '+371'},
            {'code': 'EE', 'name': 'Estonia', 'phone_code': '+372'},
            {'code': 'IE', 'name': 'Ireland', 'phone_code': '+353'},
            {'code': 'PT', 'name': 'Portugal', 'phone_code': '+351'},
            {'code': 'GR', 'name': 'Greece', 'phone_code': '+30'},
            {'code': 'CY', 'name': 'Cyprus', 'phone_code': '+357'},
            {'code': 'MT', 'name': 'Malta', 'phone_code': '+356'},
            {'code': 'LU', 'name': 'Luxembourg', 'phone_code': '+352'},
            {'code': 'AU', 'name': 'Australia', 'phone_code': '+61'},
            {'code': 'NZ', 'name': 'New Zealand', 'phone_code': '+64'},
            {'code': 'JP', 'name': 'Japan', 'phone_code': '+81'},
            {'code': 'KR', 'name': 'South Korea', 'phone_code': '+82'},
            {'code': 'CN', 'name': 'China', 'phone_code': '+86'},
            {'code': 'HK', 'name': 'Hong Kong', 'phone_code': '+852'},
            {'code': 'SG', 'name': 'Singapore', 'phone_code': '+65'},
            {'code': 'MY', 'name': 'Malaysia', 'phone_code': '+60'},
            {'code': 'TH', 'name': 'Thailand', 'phone_code': '+66'},
            {'code': 'PH', 'name': 'Philippines', 'phone_code': '+63'},
            {'code': 'ID', 'name': 'Indonesia', 'phone_code': '+62'},
            {'code': 'VN', 'name': 'Vietnam', 'phone_code': '+84'},
            {'code': 'IN', 'name': 'India', 'phone_code': '+91'},
            {'code': 'PK', 'name': 'Pakistan', 'phone_code': '+92'},
            {'code': 'BD', 'name': 'Bangladesh', 'phone_code': '+880'},
            {'code': 'LK', 'name': 'Sri Lanka', 'phone_code': '+94'},
            {'code': 'AE', 'name': 'United Arab Emirates', 'phone_code': '+971'},
            {'code': 'SA', 'name': 'Saudi Arabia', 'phone_code': '+966'},
            {'code': 'IL', 'name': 'Israel', 'phone_code': '+972'},
            {'code': 'TR', 'name': 'Turkey', 'phone_code': '+90'},
            {'code': 'RU', 'name': 'Russia', 'phone_code': '+7'},
            {'code': 'UA', 'name': 'Ukraine', 'phone_code': '+380'},
            {'code': 'BY', 'name': 'Belarus', 'phone_code': '+375'},
            {'code': 'KZ', 'name': 'Kazakhstan', 'phone_code': '+7'},
            {'code': 'ZA', 'name': 'South Africa', 'phone_code': '+27'},
            {'code': 'EG', 'name': 'Egypt', 'phone_code': '+20'},
            {'code': 'NG', 'name': 'Nigeria', 'phone_code': '+234'},
            {'code': 'KE', 'name': 'Kenya', 'phone_code': '+254'},
            {'code': 'MA', 'name': 'Morocco', 'phone_code': '+212'},
            {'code': 'BR', 'name': 'Brazil', 'phone_code': '+55'},
            {'code': 'AR', 'name': 'Argentina', 'phone_code': '+54'},
            {'code': 'CL', 'name': 'Chile', 'phone_code': '+56'},
            {'code': 'CO', 'name': 'Colombia', 'phone_code': '+57'},
            {'code': 'PE', 'name': 'Peru', 'phone_code': '+51'},
            {'code': 'MX', 'name': 'Mexico', 'phone_code': '+52'},
            {'code': 'CR', 'name': 'Costa Rica', 'phone_code': '+506'},
            {'code': 'PA', 'name': 'Panama', 'phone_code': '+507'},
        ]
    
    def get_openai_models(self):
        """Get list of available OpenAI models with metadata"""
        return [
            {
                'key': 'gpt-4.1',
                'name': 'GPT-4.1',
                'description': 'Premium flagship model for complex reasoning and multimodal tasks',
                'cost_tier': 'premium',
                'capabilities': ['text', 'vision', 'tools'],
                'recommended_for': ['complex reasoning', 'analysis', 'creative writing']
            },
            {
                'key': 'gpt-4.1-mini',
                'name': 'GPT-4.1 Mini',
                'description': 'Cost-effective model performing almost as well as GPT-4.1 at 1/5th the price',
                'cost_tier': 'standard',
                'capabilities': ['text', 'vision', 'tools'],
                'recommended_for': ['general use', 'most applications', 'cost-sensitive scenarios']
            },
            {
                'key': 'o3',
                'name': 'OpenAI o3',
                'description': 'Latest reasoning model trained to think longer before responding',
                'cost_tier': 'premium',
                'capabilities': ['text', 'reasoning', 'tools'],
                'recommended_for': ['complex problem solving', 'mathematical reasoning', 'analysis']
            },
            {
                'key': 'o4-mini',
                'name': 'OpenAI o4-mini',
                'description': 'Smaller reasoning model optimized for fast, cost-efficient reasoning',
                'cost_tier': 'standard',
                'capabilities': ['text', 'reasoning', 'math', 'coding'],
                'recommended_for': ['math problems', 'coding tasks', 'quick reasoning']
            },
            {
                'key': 'o3-mini',
                'name': 'OpenAI o3-mini',
                'description': 'Latest compact reasoning model with enhanced capabilities',
                'cost_tier': 'standard',
                'capabilities': ['text', 'reasoning'],
                'recommended_for': ['reasoning tasks', 'problem solving', 'analysis']
            },
            {
                'key': 'gpt-4o',
                'name': 'GPT-4o',
                'description': 'Multimodal model integrating text and images in a single model',
                'cost_tier': 'standard',
                'capabilities': ['text', 'vision', 'multimodal'],
                'recommended_for': ['image analysis', 'visual content', 'multimodal tasks']
            },
            {
                'key': 'gpt-3.5-turbo',
                'name': 'GPT-3.5 Turbo',
                'description': 'Most capable and cost-effective model in the GPT-3.5 family',
                'cost_tier': 'budget',
                'capabilities': ['text'],
                'recommended_for': ['simple tasks', 'budget-conscious applications', 'basic automation']
            }
        ]
    
    def get_record_data_options(self):
        """Get available record data field options"""
        return {
            'timestamp': [
                {'key': 'created_at', 'label': 'Created At', 'description': 'When record was created'},
                {'key': 'updated_at', 'label': 'Updated At', 'description': 'When record was last modified'},
                {'key': 'last_engaged_at', 'label': 'Last Engaged At', 'description': 'Last user interaction (comment, edit, view)'},
                {'key': 'first_contacted_at', 'label': 'First Contacted At', 'description': 'First communication sent'},
                {'key': 'last_contacted_at', 'label': 'Last Contacted At', 'description': 'Most recent communication'},
                {'key': 'last_response_at', 'label': 'Last Response At', 'description': 'Most recent response received'},
                {'key': 'next_followup_at', 'label': 'Next Follow-up At', 'description': 'Scheduled next contact'},
                {'key': 'stage_entered_at', 'label': 'Stage Entered At', 'description': 'When current stage was entered'},
                {'key': 'deal_closed_at', 'label': 'Deal Closed At', 'description': 'When deal/opportunity closed'},
            ],
            'user': [
                {'key': 'created_by', 'label': 'Created By', 'description': 'User who created record'},
                {'key': 'updated_by', 'label': 'Updated By', 'description': 'User who last modified record'},
                {'key': 'first_contacted_by', 'label': 'First Contacted By', 'description': 'User who made first contact'},
                {'key': 'last_contacted_by', 'label': 'Last Contacted By', 'description': 'User who sent last communication'},
            ],
            'count': [
                {'key': 'total_communications', 'label': 'Total Communications', 'description': 'Total emails/calls/messages'},
                {'key': 'total_meetings', 'label': 'Total Meetings', 'description': 'Total scheduled meetings'},
                {'key': 'total_notes', 'label': 'Total Notes', 'description': 'Total notes/comments'},
                {'key': 'days_in_pipeline', 'label': 'Days in Pipeline', 'description': 'Days since record created'},
                {'key': 'days_in_stage', 'label': 'Days in Stage', 'description': 'Days in current stage'},
                {'key': 'total_tasks', 'label': 'Total Tasks', 'description': 'Total tasks created'},
                {'key': 'open_tasks', 'label': 'Open Tasks', 'description': 'Currently open tasks'},
            ],
            'duration': [
                {'key': 'time_to_response', 'label': 'Time to Response', 'description': 'Average response time'},
                {'key': 'stage_duration', 'label': 'Stage Duration', 'description': 'Time spent in current stage'},
                {'key': 'total_cycle_time', 'label': 'Total Cycle Time', 'description': 'Total time from creation to close'},
                {'key': 'time_since_contact', 'label': 'Time Since Contact', 'description': 'Time since last communication'},
            ],
            'status': [
                {'key': 'engagement_status', 'label': 'Engagement Status', 'description': 'Active, Stale, Cold (based on last contact)'},
                {'key': 'response_status', 'label': 'Response Status', 'description': 'Responsive, Slow, Unresponsive'},
                {'key': 'pipeline_health', 'label': 'Pipeline Health', 'description': 'On Track, At Risk, Stalled'},
                {'key': 'communication_status', 'label': 'Communication Status', 'description': 'Recent, Overdue, Never Contacted'},
            ]
        }
    
    def list(self, request):
        """Get all global options"""
        return Response({
            'currencies': self.get_currencies(),
            'countries': self.get_countries(),
            'openai_models': self.get_openai_models(),
            'record_data_options': self.get_record_data_options()
        })
    
    @action(detail=False, methods=['get'])
    def currencies(self, request):
        """Get supported currencies"""
        return Response(self.get_currencies())
    
    @action(detail=False, methods=['get'])
    def countries(self, request):
        """Get supported countries with phone codes"""
        return Response(self.get_countries())
    
    @action(detail=False, methods=['get'])
    def openai_models(self, request):
        """Get available OpenAI models"""
        return Response(self.get_openai_models())
    
    @action(detail=False, methods=['get'])
    def record_data_options(self, request):
        """Get record data field options"""
        return Response(self.get_record_data_options())