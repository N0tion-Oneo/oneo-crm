// RealtimeEventService - Handles WebSocket message processing and state updates
import { Record, Pipeline } from '@/types/records'
import { type RealtimeMessage } from '@/contexts/websocket-context'

export interface RealtimeUpdateHandlers {
  onRecordCreate: (record: Record) => void
  onRecordUpdate: (record: Record) => void
  onRecordDelete: (recordId: string) => void
  onError: (error: Error) => void
}

export class RealtimeEventService {
  /**
   * Process incoming WebSocket message and trigger appropriate handlers
   */
  static processMessage(
    message: RealtimeMessage,
    pipelineId: string,
    handlers: RealtimeUpdateHandlers
  ): void {
    console.log('📨 Processing realtime message:', message)
    console.log('🔍 Pipeline comparison:', {
      messagePipelineId: message.payload?.pipeline_id,
      currentPipelineId: pipelineId,
      matches: String(message.payload?.pipeline_id) === String(pipelineId)
    })

    // Only process messages for the current pipeline
    if (String(message.payload?.pipeline_id) !== String(pipelineId)) {
      console.log('❌ Pipeline ID mismatch, ignoring message')
      return
    }

    try {
      switch (message.type) {
        case 'record_create':
          this.handleRecordCreate(message, handlers.onRecordCreate)
          break
          
        case 'record_update':
          this.handleRecordUpdate(message, handlers.onRecordUpdate)
          break
          
        case 'record_delete':
          this.handleRecordDelete(message, handlers.onRecordDelete)
          break
          
        default:
          console.log('⚠️ Unknown message type:', message.type)
      }
    } catch (error) {
      console.error('❌ Error processing realtime message:', error)
      handlers.onError(error as Error)
    }
  }

  /**
   * Handle record creation message
   */
  private static handleRecordCreate(
    message: RealtimeMessage, 
    onRecordCreate: (record: Record) => void
  ): void {
    const newRecord: Record = {
      id: message.payload.record_id,
      data: message.payload.data || {},
      created_at: message.payload.updated_at || new Date().toISOString(),
      updated_at: message.payload.updated_at || new Date().toISOString(),
      created_by: message.payload.updated_by
    }

    console.log('✅ Processing record creation:', newRecord.id)
    onRecordCreate(newRecord)
  }

  /**
   * Handle record update message
   */
  private static handleRecordUpdate(
    message: RealtimeMessage,
    onRecordUpdate: (record: Record) => void
  ): void {
    const updatedRecord: Record = {
      id: message.payload.record_id,
      data: message.payload.data || {},
      updated_at: message.payload.updated_at || new Date().toISOString(),
      created_at: '', // Will be merged with existing data
      created_by: message.payload.updated_by
    }

    // Check if this is a relationship change
    const isRelationshipChange = message.payload.relationship_changed === true

    // Identify relation fields in the data
    const relationFields = Object.keys(updatedRecord.data).filter(key => {
      const value = updatedRecord.data[key]
      return (
        Array.isArray(value) ||
        (typeof value === 'object' && value !== null && 'id' in value && 'display_value' in value)
      )
    })

    console.log('🔄 Processing record update:', {
      recordId: updatedRecord.id,
      updatedFields: Object.keys(updatedRecord.data),
      isRelationshipChange,
      relationFields,
      relationFieldCount: relationFields.length
    })

    if (isRelationshipChange) {
      console.log('🔗 Relationship change detected - relation fields updated:', relationFields)
    }

    onRecordUpdate(updatedRecord)
  }

  /**
   * Handle record deletion message
   */
  private static handleRecordDelete(
    message: RealtimeMessage, 
    onRecordDelete: (recordId: string) => void
  ): void {
    const deletedRecordId = message.payload.record_id
    console.log('🗑️ Processing record deletion:', deletedRecordId)
    onRecordDelete(deletedRecordId)
  }

  /**
   * Merge updated record with existing record data
   */
  static mergeRecordUpdate(existingRecord: Record, updatedRecord: Record): Record {
    const mergedRecord = {
      ...existingRecord,
      ...updatedRecord,
      data: {
        ...existingRecord.data,
        ...updatedRecord.data
      },
      // Preserve creation info from existing record
      created_at: existingRecord.created_at
    }

    console.log('🔄 Merging record data:', {
      recordId: existingRecord.id,
      originalFields: Object.keys(existingRecord.data),
      updatedFields: Object.keys(updatedRecord.data),
      mergedFields: Object.keys(mergedRecord.data)
    })

    return mergedRecord
  }

  /**
   * Update records array with new record
   */
  static updateRecordsArray(
    records: Record[], 
    updatedRecord: Record
  ): Record[] {
    return records.map(record => 
      String(record.id) === String(updatedRecord.id) 
        ? this.mergeRecordUpdate(record, updatedRecord)
        : record
    )
  }

  /**
   * Add new record to records array (at the beginning for recent-first display)
   */
  static addRecordToArray(records: Record[], newRecord: Record): Record[] {
    return [newRecord, ...records]
  }

  /**
   * Remove record from records array
   */
  static removeRecordFromArray(records: Record[], recordId: string): Record[] {
    return records.filter(record => String(record.id) !== String(recordId))
  }

  /**
   * Generate WebSocket channel name for pipeline
   */
  static getPipelineChannelName(pipelineId: string): string {
    return `pipeline_records_${pipelineId}`
  }

  /**
   * Log WebSocket connection status
   */
  static logConnectionStatus(
    pipelineId: string, 
    isConnected: boolean, 
    recordCount: number
  ): void {
    console.log('🔌 REALTIME STATUS:', {
      pipelineId,
      channel: this.getPipelineChannelName(pipelineId),
      isConnected,
      recordCount,
      timestamp: new Date().toISOString()
    })

    if (isConnected) {
      console.log('✅ WebSocket CONNECTED - Ready for real-time updates')
    } else {
      console.log('❌ WebSocket DISCONNECTED - Real-time updates unavailable')
    }
  }
}