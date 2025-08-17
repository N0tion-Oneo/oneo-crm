"""
API serializers for communications account management
"""
from rest_framework import serializers
from communications.models import UserChannelConnection, ChannelType


class UserChannelConnectionSerializer(serializers.ModelSerializer):
    """Serializer for user channel connections (frontend-friendly)"""
    
    channelType = serializers.CharField(source='channel_type', read_only=True)
    accountName = serializers.CharField(source='account_name', read_only=True)
    authStatus = serializers.CharField(source='auth_status', read_only=True)
    accountStatus = serializers.CharField(source='account_status', read_only=True)
    externalAccountId = serializers.CharField(source='unipile_account_id', read_only=True)
    hostedAuthUrl = serializers.CharField(source='hosted_auth_url', read_only=True)
    lastActiveAt = serializers.DateTimeField(source='last_sync_at', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    
    # Enhanced status information
    statusInfo = serializers.SerializerMethodField()
    canSendMessages = serializers.SerializerMethodField()
    channelId = serializers.SerializerMethodField()  # Associated Channel ID for WebSocket subscriptions
    lastError = serializers.CharField(source='last_error', read_only=True)
    checkpointData = serializers.JSONField(source='checkpoint_data', read_only=True)
    messagesSentToday = serializers.IntegerField(source='messages_sent_today', read_only=True)
    rateLimitPerHour = serializers.IntegerField(source='rate_limit_per_hour', read_only=True)
    
    class Meta:
        model = UserChannelConnection
        fields = [
            'id', 'channelType', 'accountName', 'authStatus', 'accountStatus',
            'externalAccountId', 'hostedAuthUrl', 'lastActiveAt', 'createdAt',
            'statusInfo', 'canSendMessages', 'channelId', 'lastError', 'checkpointData',
            'messagesSentToday', 'rateLimitPerHour'
        ]
    
    def get_statusInfo(self, obj):
        """Get detailed status information for frontend display"""
        return obj.get_status_display_info()
    
    def get_canSendMessages(self, obj):
        """Check if account can send messages"""
        return obj.can_send_messages()
    
    def get_channelId(self, obj):
        """Get the associated Channel ID for WebSocket subscriptions"""
        from communications.models import Channel
        try:
            channel = Channel.objects.filter(
                unipile_account_id=obj.unipile_account_id,
                channel_type=obj.channel_type
            ).first()
            return str(channel.id) if channel else None
        except Exception:
            return None


class AccountConnectionSerializer(serializers.ModelSerializer):
    """Serializer for user channel connections"""
    
    status_info = serializers.SerializerMethodField()
    can_send_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = UserChannelConnection
        fields = [
            'id', 'channel_type', 'account_name', 'auth_status', 'account_status',
            'hosted_auth_url', 'is_active', 'last_sync_at', 'sync_error_count',
            'last_error', 'messages_sent_today', 'rate_limit_per_hour',
            'created_at', 'updated_at', 'status_info', 'can_send_messages'
        ]
        read_only_fields = [
            'id', 'auth_status', 'account_status', 'hosted_auth_url', 'last_sync_at',
            'sync_error_count', 'last_error', 'messages_sent_today', 'created_at',
            'updated_at', 'status_info', 'can_send_messages'
        ]
    
    def get_status_info(self, obj):
        """Get detailed status information"""
        return obj.get_status_display_info()
    
    def get_can_send_messages(self, obj):
        """Check if account can send messages"""
        return obj.can_send_messages()


class StartConnectionSerializer(serializers.Serializer):
    """Serializer for starting account connection"""
    
    channel_type = serializers.ChoiceField(choices=ChannelType.choices)
    account_name = serializers.CharField(max_length=255, required=False)
    redirect_url = serializers.URLField(required=False)
    
    def validate_redirect_url(self, value):
        """Validate redirect URL"""
        if not value:
            # Default to frontend callback URL
            request = self.context.get('request')
            if request:
                scheme = 'https' if request.is_secure() else 'http'
                host = request.get_host()
                return f"{scheme}://{host}/auth/callback"
        return value


class HandleCallbackSerializer(serializers.Serializer):
    """Serializer for handling auth callback"""
    
    connection_id = serializers.UUIDField()
    provider_data = serializers.JSONField(required=False)
    
    def validate_connection_id(self, value):
        """Validate connection exists and belongs to user"""
        request = self.context.get('request')
        if request and request.user:
            try:
                connection = UserChannelConnection.objects.get(
                    id=value,
                    user=request.user
                )
                return value
            except UserChannelConnection.DoesNotExist:
                raise serializers.ValidationError("Connection not found or not owned by user")
        raise serializers.ValidationError("Authentication required")


class SolveCheckpointSerializer(serializers.Serializer):
    """Serializer for solving checkpoints"""
    
    connection_id = serializers.UUIDField()
    verification_code = serializers.CharField(max_length=20)
    
    def validate_connection_id(self, value):
        """Validate connection exists and belongs to user"""
        request = self.context.get('request')
        if request and request.user:
            try:
                connection = UserChannelConnection.objects.get(
                    id=value,
                    user=request.user,
                    account_status='checkpoint_required'
                )
                return value
            except UserChannelConnection.DoesNotExist:
                raise serializers.ValidationError("Connection not found or doesn't require checkpoint")
        raise serializers.ValidationError("Authentication required")


class AccountStatusSerializer(serializers.ModelSerializer):
    """Lightweight serializer for account status"""
    
    status_info = serializers.SerializerMethodField()
    
    class Meta:
        model = UserChannelConnection
        fields = [
            'id', 'account_name', 'channel_type', 'account_status', 
            'auth_status', 'last_sync_at', 'last_error', 'status_info'
        ]
    
    def get_status_info(self, obj):
        """Get detailed status information"""
        return obj.get_status_display_info()