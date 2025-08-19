/**
 * WhatsApp Identity Handler - Ensures proper separation between business account and customer contacts
 */

interface WhatsAppContact {
  whatsapp_id: string;
  phone_number: string;
  name?: string;
  attendee_id?: string;
  profile_picture?: string;
  is_business_account?: boolean;
}

interface WhatsAppMessage {
  id: string;
  content: string;
  direction: 'inbound' | 'outbound';
  contact_email: string;
  metadata?: {
    contact_name?: string;
    sender_attendee_id?: string;
    chat_id?: string;
    from?: string;
    to?: string;
    is_sender?: number;
    profile_picture?: string;
  };
  timestamp: string;
  channel?: {
    name: string;
    channel_type: string;
  };
}

interface WhatsAppConversation {
  id: string;
  contact: WhatsAppContact;
  last_message: WhatsAppMessage;
  unread_count: number;
  chat_id: string;
  business_account_id: string;
}

export class WhatsAppIdentityHandler {
  // Known business accounts - should be fetched from connection data
  private static BUSINESS_ACCOUNTS = new Set([
    '27720720047@s.whatsapp.net', // OneOTalent business number
    // Add other business accounts as needed
  ]);

  /**
   * Determine if a WhatsApp ID represents the business account
   */
  static isBusinessAccount(whatsappId: string): boolean {
    return this.BUSINESS_ACCOUNTS.has(whatsappId);
  }

  /**
   * Extract contact name using provider logic - the contact we're speaking to
   */
  static getContactName(message: WhatsAppMessage, isBusinessSide: boolean = false): string {
    // If this is the business side, show business name
    if (isBusinessSide) {
      return "OneOTalent Business";
    }

    // For customer contacts, use provider logic - always get the contact we're speaking to
    const metadata = message.metadata || {};
    const rawWebhookData = metadata.raw_webhook_data || {};
    
    // 1. Try contact_name from metadata (extracted using provider logic)
    if (metadata.contact_name && 
        metadata.contact_name !== message.contact_email &&
        !metadata.contact_name.includes('@s.whatsapp.net') &&
        !metadata.contact_name.match(/^\d+$/)) {
      return metadata.contact_name;
    }

    // 2. Extract from raw webhook data using provider logic
    if (rawWebhookData.provider_chat_id) {
      const providerChatId = rawWebhookData.provider_chat_id;
      
      // Find attendee matching provider_chat_id
      const attendees = rawWebhookData.attendees || [];
      for (const attendee of attendees) {
        if (attendee.attendee_provider_id === providerChatId && 
            attendee.attendee_name &&
            attendee.attendee_name !== attendee.attendee_provider_id &&
            !attendee.attendee_name.includes('@s.whatsapp.net') &&
            !attendee.attendee_name.match(/^\d+$/)) {
          return attendee.attendee_name;
        }
      }
      
      // Check if sender matches provider_chat_id (inbound case)
      const sender = rawWebhookData.sender;
      if (sender && sender.attendee_provider_id === providerChatId &&
          sender.attendee_name &&
          sender.attendee_name !== sender.attendee_provider_id &&
          !sender.attendee_name.includes('@s.whatsapp.net') &&
          !sender.attendee_name.match(/^\d+$/)) {
        return sender.attendee_name;
      }
    }

    // 3. Extract and format phone number from contact_phone field (new approach)
    let phoneNumber = message.contact_phone;
    
    // Fallback to contact_email format for legacy messages
    if (!phoneNumber) {
      const contactEmail = message.contact_email;
      if (contactEmail && contactEmail.includes('@s.whatsapp.net')) {
        phoneNumber = contactEmail.replace('@s.whatsapp.net', '');
        // Add country code formatting if not present
        if (!phoneNumber.startsWith('+')) {
          phoneNumber = `+${phoneNumber}`;
        }
      }
    }
    
    // 4. Check known contact mapping if we have a phone number
    if (phoneNumber) {
      // Remove + prefix for lookup
      const cleanPhone = phoneNumber.replace('+', '');
      
      // Known contact mapping (based on our analysis)
      const knownContacts: Record<string, string> = {
        '27849977040': 'Vanessa',
        '27836851686': 'Warren', 
        '27836587900': 'Pearl',
        '27720720057': 'Robbie Cowan',
        '27665830939': 'Contact +27 66 583 0939',
        '27725750914': 'Contact +27 72 575 0914'
      };
      
      // Check if this is a known contact
      if (knownContacts[cleanPhone]) {
        return knownContacts[cleanPhone];
      }
      
      // Format phone number nicely (South African format)
      if (cleanPhone.startsWith('27') && cleanPhone.length === 11) {
        return `+${cleanPhone.slice(0, 2)} ${cleanPhone.slice(2, 5)} ${cleanPhone.slice(5, 8)} ${cleanPhone.slice(8)}`;
      }
      
      // Format UK numbers
      if (cleanPhone.startsWith('44') && cleanPhone.length >= 10) {
        return `+${cleanPhone.slice(0, 2)} ${cleanPhone.slice(2, 5)} ${cleanPhone.slice(5, 8)} ${cleanPhone.slice(8)}`;
      }
      
      // Return formatted phone with + prefix
      return phoneNumber.startsWith('+') ? phoneNumber : `+${phoneNumber}`;
    }

    // 4. Fallback to email/ID or unknown
    return message.contact_email || 'Unknown Contact';
  }

  /**
   * Get profile picture URL from UniPile metadata
   */
  static getProfilePicture(message: WhatsAppMessage): string | null {
    const metadata = message.metadata || {};
    
    // Try profile picture from metadata
    if (metadata.profile_picture) {
      return metadata.profile_picture;
    }

    // Construct UniPile profile picture URL if we have attendee ID
    if (metadata.sender_attendee_id && message.contact_email && message.contact_email.includes('@s.whatsapp.net')) {
      const accountId = 'mp9Gis3IRtuh9V5oSxZdSA'; // Should be dynamic from connection data
      return `wapp://${accountId}/${message.contact_email}.jpg`;
    }

    return null;
  }

  /**
   * Get the customer contact from a WhatsApp conversation (never the business)
   */
  static getCustomerContactFromConversation(messages: WhatsAppMessage[]): WhatsAppContact | null {
    try {
      if (!messages || !messages.length) {
        return null;
      }

      // Filter out messages with null/undefined contact_email first
      const validMessages = messages.filter(msg => {
        return msg && typeof msg === 'object' && msg.contact_email && typeof msg.contact_email === 'string';
      });
      
      if (!validMessages.length) {
        console.warn('⚠️ No messages with valid contact_email found');
        return null;
      }

      // Find any message from a customer (not business) to identify the contact
      const customerMessage = validMessages.find(msg => {
        try {
          return !this.isBusinessAccount(msg.contact_email);
        } catch (e) {
          return false;
        }
      });
      
      if (!customerMessage || !customerMessage.contact_email) {
        console.warn('⚠️ No customer messages found in conversation - all messages from business?');
        return null;
      }

      const metadata = customerMessage.metadata || {};
      
      return {
        whatsapp_id: customerMessage.contact_email,
        phone_number: customerMessage.contact_email.replace('@s.whatsapp.net', ''),
        name: this.getContactName(customerMessage, false),
        attendee_id: metadata.sender_attendee_id || '',
        profile_picture: this.getProfilePicture(customerMessage) || undefined,
        is_business_account: false
      };
    } catch (error) {
      console.error('Error in getCustomerContactFromConversation:', error);
      return null;
    }
  }

  /**
   * Format WhatsApp conversation for unified inbox display
   */
  static formatConversation(messages: WhatsAppMessage[]): WhatsAppConversation | null {
    if (!messages.length) return null;

    const latestMessage = messages[0]; // Assuming messages are sorted by timestamp desc
    const customerContact = this.getCustomerContactFromConversation(messages);
    
    if (!customerContact) {
      return null;
    }

    const metadata = latestMessage.metadata || {};

    return {
      id: metadata.chat_id || `chat_${customerContact.whatsapp_id}`,
      contact: customerContact,
      last_message: latestMessage,
      unread_count: messages.filter(m => m.direction === 'inbound' && !(m.metadata as any)?.seen).length,
      chat_id: metadata.chat_id || '',
      business_account_id: 'mp9Gis3IRtuh9V5oSxZdSA' // Should be dynamic
    };
  }

  /**
   * Format message display with proper identity labels
   */
  static formatMessageDisplay(message: WhatsAppMessage, currentUserEmail?: string): {
    senderName: string;
    isFromBusiness: boolean;
    isFromCurrentUser: boolean;
    displayAvatar: string | null;
  } {
    const isFromBusiness = this.isBusinessAccount(message.contact_email || '');
    const isFromCurrentUser = message.direction === 'outbound' || isFromBusiness;

    return {
      senderName: this.getContactName(message, isFromBusiness),
      isFromBusiness,
      isFromCurrentUser,
      displayAvatar: this.getProfilePicture(message)
    };
  }

  /**
   * Validate that we never show the business phone as a "contact"
   */
  static validateContactDisplay(contact: WhatsAppContact): boolean {
    if (contact.is_business_account) {
      console.warn('⚠️ Business account should not be displayed as a contact:', contact);
      return false;
    }

    if (this.isBusinessAccount(contact.whatsapp_id)) {
      console.warn('⚠️ Business WhatsApp ID should not be displayed as a contact:', contact.whatsapp_id);
      return false;
    }

    return true;
  }

  /**
   * Get message direction label for UI
   */
  static getDirectionLabel(message: WhatsAppMessage): string {
    const isFromBusiness = this.isBusinessAccount(message.contact_email || '');
    
    if (message.direction === 'outbound' || isFromBusiness) {
      return 'You sent';
    } else {
      return `${this.getContactName(message)} sent`;
    }
  }

  /**
   * Extract all customer contacts from WhatsApp messages
   */
  static extractCustomerContacts(messages: WhatsAppMessage[]): WhatsAppContact[] {
    const contactMap = new Map<string, WhatsAppContact>();

    messages.forEach(message => {
      const metadata = message.metadata || {};
      
      // Skip business account messages or messages without contact_email
      if (!message.contact_email || this.isBusinessAccount(message.contact_email)) {
        return;
      }

      const contact: WhatsAppContact = {
        whatsapp_id: message.contact_email,
        phone_number: message.contact_email.replace('@s.whatsapp.net', ''),
        name: this.getContactName(message, false),
        attendee_id: metadata.sender_attendee_id,
        profile_picture: this.getProfilePicture(message) || undefined,
        is_business_account: false
      };

      // Validate contact display
      if (this.validateContactDisplay(contact)) {
        contactMap.set(contact.whatsapp_id, contact);
      }
    });

    return Array.from(contactMap.values());
  }
}