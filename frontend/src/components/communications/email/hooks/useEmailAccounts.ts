import { useState, useEffect, useCallback } from 'react'
import { emailService } from '@/services/emailService'
import { useToast } from '@/hooks/use-toast'
import { EmailAccount } from '../utils/emailTypes'

export const useEmailAccounts = () => {
  const [accounts, setAccounts] = useState<EmailAccount[]>([])
  const [selectedAccount, setSelectedAccount] = useState<EmailAccount | null>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  const loadAccounts = useCallback(async () => {
    try {
      setLoading(true)
      const result = await emailService.getAccounts()
      
      if (result.success && result.accounts.length > 0) {
        setAccounts(result.accounts)
        // Auto-select first account if none selected
        if (!selectedAccount) {
          setSelectedAccount(result.accounts[0])
        }
      } else if (result.accounts.length === 0) {
        toast({
          title: 'No email accounts',
          description: 'No email accounts connected. Please connect an email account first.',
          variant: 'default'
        })
      }
    } catch (error) {
      console.error('Failed to load email accounts:', error)
      toast({
        title: 'Error loading accounts',
        description: 'Failed to load email accounts. Please try again.',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }, [selectedAccount, toast])

  // Load accounts on mount
  useEffect(() => {
    loadAccounts()
  }, []) // Only run on mount, not when loadAccounts changes

  const selectAccount = useCallback((account: EmailAccount) => {
    setSelectedAccount(account)
  }, [])

  return {
    accounts,
    selectedAccount,
    loading,
    loadAccounts,
    selectAccount
  }
}