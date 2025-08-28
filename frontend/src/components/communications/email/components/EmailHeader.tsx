import React from 'react'
import { Search, Filter, RefreshCw, Plus, Folder } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectSeparator } from '@/components/ui/select'
import { EmailAccount, EmailFolder } from '../utils/emailTypes'
import { getFolderDisplayName, isSystemFolder } from '../utils/emailFormatters'

interface EmailHeaderProps {
  accounts: EmailAccount[]
  selectedAccount: EmailAccount | null
  onAccountSelect: (account: EmailAccount) => void
  searchQuery: string
  onSearchChange: (query: string) => void
  filterStatus: 'all' | 'unread' | 'starred'
  onFilterChange: (status: 'all' | 'unread' | 'starred') => void
  selectedFolder: string
  onFolderChange: (folder: string) => void
  folders: EmailFolder[]
  syncing: boolean
  onSync: () => void
  onCompose: () => void
  loading?: boolean
}

export const EmailHeader: React.FC<EmailHeaderProps> = ({
  accounts,
  selectedAccount,
  onAccountSelect,
  searchQuery,
  onSearchChange,
  filterStatus,
  onFilterChange,
  selectedFolder,
  onFolderChange,
  folders,
  syncing,
  onSync,
  onCompose,
  loading = false
}) => {
  return (
    <div className="border-b bg-white dark:bg-gray-950">
      <div className="flex items-center justify-between p-4 gap-4">
        {/* Left side - Account selector and compose */}
        <div className="flex items-center gap-2">
          {/* Account Selector */}
          <Select 
            value={selectedAccount?.account_id || ''} 
            onValueChange={(value) => {
              const account = accounts.find(a => a.account_id === value)
              if (account) onAccountSelect(account)
            }}
            disabled={loading}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select account">
                {selectedAccount ? selectedAccount.email : 'Select account'}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {accounts.map(account => (
                <SelectItem key={account.account_id} value={account.account_id}>
                  <div className="flex flex-col">
                    <span>{account.email}</span>
                    <span className="text-xs text-muted-foreground">
                      {account.provider}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* Compose Button */}
          <Button 
            onClick={onCompose}
            disabled={!selectedAccount || loading}
            size="sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            Compose
          </Button>
        </div>

        {/* Center - Search */}
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="search"
              placeholder="Search emails..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              disabled={!selectedAccount || loading}
            />
          </div>
        </div>

        {/* Right side - Filters and actions */}
        <div className="flex items-center gap-2">
          {/* Folder Selector */}
          <Select 
            value={selectedFolder} 
            onValueChange={onFolderChange}
            disabled={!selectedAccount || loading}
          >
            <SelectTrigger className="w-[150px]">
              <div className="flex items-center gap-2">
                <Folder className="w-4 h-4" />
                <SelectValue placeholder="Folder" />
              </div>
            </SelectTrigger>
            <SelectContent>
              {folders.length > 0 ? (
                <>
                  {/* System folders */}
                  {folders
                    .filter(f => isSystemFolder(f.role))
                    .sort((a, b) => {
                      const order = ['inbox', 'sent', 'drafts', 'trash', 'spam', 'all', 'important', 'starred']
                      return order.indexOf(a.role || '') - order.indexOf(b.role || '')
                    })
                    .map(folder => (
                      <SelectItem 
                        key={folder.id || folder.provider_id} 
                        value={folder.provider_id || folder.id || folder.name}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span className="font-medium">{getFolderDisplayName(folder)}</span>
                          {folder.nb_mails !== undefined && folder.nb_mails > 0 && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              {folder.nb_mails}
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  }
                  
                  {/* Separator if there are custom folders */}
                  {folders.some(f => !isSystemFolder(f.role)) && 
                   folders.some(f => isSystemFolder(f.role)) && (
                    <SelectSeparator />
                  )}
                  
                  {/* Custom/Label folders */}
                  {folders
                    .filter(f => !isSystemFolder(f.role))
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map(folder => (
                      <SelectItem 
                        key={folder.id || folder.provider_id} 
                        value={folder.provider_id || folder.id || folder.name}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span>{folder.name}</span>
                          {folder.nb_mails !== undefined && folder.nb_mails > 0 && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              {folder.nb_mails}
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  }
                </>
              ) : (
                // Fallback to default folders if no folders loaded
                <>
                  <SelectItem value="INBOX">Inbox</SelectItem>
                  <SelectItem value="[Gmail]/Sent Mail">Sent</SelectItem>
                  <SelectItem value="[Gmail]/Drafts">Drafts</SelectItem>
                  <SelectItem value="[Gmail]/Trash">Trash</SelectItem>
                  <SelectItem value="[Gmail]/Spam">Spam</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>

          {/* Filter Status */}
          <Select 
            value={filterStatus} 
            onValueChange={(value: any) => onFilterChange(value)}
            disabled={!selectedAccount || loading}
          >
            <SelectTrigger className="w-28">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="unread">Unread</SelectItem>
              <SelectItem value="starred">Starred</SelectItem>
            </SelectContent>
          </Select>

          {/* Sync Button */}
          <Button 
            variant="outline" 
            size="sm"
            onClick={onSync}
            disabled={!selectedAccount || syncing || loading}
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>
    </div>
  )
}