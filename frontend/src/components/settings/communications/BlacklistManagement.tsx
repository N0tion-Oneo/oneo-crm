'use client'

import { useState } from 'react'
import { Shield, Plus, Trash2, AlertCircle, Search } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useToast } from '@/hooks/use-toast'

interface BlacklistEntry {
  id: string
  entry_type: 'domain' | 'email' | 'email_pattern' | 'phone' | 'name_pattern'
  value: string
  reason: string
  is_active: boolean
  expires_at: string | null
  created_by_name: string
  created_at: string
}

interface BlacklistManagementProps {
  blacklist: BlacklistEntry[]
  onAddEntry: (entry: any) => Promise<void>
  onRemoveEntry: (id: string) => Promise<void>
  canEdit: boolean
}

const ENTRY_TYPE_LABELS = {
  domain: { label: 'Domain', icon: '🌐', example: 'example.com' },
  email: { label: 'Email Address', icon: '📧', example: 'user@example.com' },
  email_pattern: { label: 'Email Pattern', icon: '📋', example: '*@spam.com' },
  phone: { label: 'Phone Number', icon: '📱', example: '+1234567890' },
  name_pattern: { label: 'Name Pattern', icon: '👤', example: 'Test*' }
}

export function BlacklistManagement({
  blacklist,
  onAddEntry,
  onRemoveEntry,
  canEdit
}: BlacklistManagementProps) {
  const { toast } = useToast()
  const [showDialog, setShowDialog] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [newEntry, setNewEntry] = useState({
    entry_type: 'email' as keyof typeof ENTRY_TYPE_LABELS,
    value: '',
    reason: ''
  })

  const handleAddEntry = async () => {
    if (!newEntry.value) {
      toast({
        title: "Validation Error",
        description: "Please provide a value for the blacklist entry",
        variant: "destructive",
      })
      return
    }

    try {
      await onAddEntry(newEntry)
      setShowDialog(false)
      setNewEntry({ entry_type: 'email', value: '', reason: '' })
      toast({
        title: "Entry Added",
        description: "Blacklist entry has been added successfully.",
      })
    } catch (error) {
      toast({
        title: "Failed to add entry",
        description: "An error occurred while adding the blacklist entry.",
        variant: "destructive",
      })
    }
  }

  const handleRemoveEntry = async (id: string) => {
    try {
      await onRemoveEntry(id)
      toast({
        title: "Entry Removed",
        description: "Blacklist entry has been removed.",
      })
    } catch (error) {
      toast({
        title: "Failed to remove entry",
        description: "An error occurred while removing the entry.",
        variant: "destructive",
      })
    }
  }

  const filteredBlacklist = blacklist.filter(entry =>
    entry.value.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.reason?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.entry_type.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <div>
              <CardTitle>Blacklist Management</CardTitle>
              <CardDescription>
                Prevent specific participants from being auto-created
              </CardDescription>
            </div>
          </div>
          {canEdit && (
            <Dialog open={showDialog} onOpenChange={setShowDialog}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Entry
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Blacklist Entry</DialogTitle>
                  <DialogDescription>
                    Add a pattern to prevent specific participants from auto-creation
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>Entry Type</Label>
                    <Select
                      value={newEntry.entry_type}
                      onValueChange={(value: keyof typeof ENTRY_TYPE_LABELS) => 
                        setNewEntry({ ...newEntry, entry_type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(ENTRY_TYPE_LABELS).map(([key, config]) => (
                          <SelectItem key={key} value={key}>
                            <div className="flex items-center gap-2">
                              <span>{config.icon}</span>
                              <span>{config.label}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Value</Label>
                    <Input
                      placeholder={ENTRY_TYPE_LABELS[newEntry.entry_type].example}
                      value={newEntry.value}
                      onChange={(e) => setNewEntry({ ...newEntry, value: e.target.value })}
                    />
                    <p className="text-xs text-gray-500">
                      {newEntry.entry_type === 'email_pattern' || newEntry.entry_type === 'name_pattern'
                        ? 'Use * for wildcards (e.g., *@spam.com)'
                        : `Enter a specific ${ENTRY_TYPE_LABELS[newEntry.entry_type].label.toLowerCase()}`}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Reason (Optional)</Label>
                    <Textarea
                      placeholder="Why is this being blacklisted?"
                      value={newEntry.reason}
                      onChange={(e) => setNewEntry({ ...newEntry, reason: e.target.value })}
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleAddEntry}>
                    Add Entry
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Search Bar */}
        <div className="mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search blacklist entries..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Blacklist Table */}
        {filteredBlacklist.length === 0 ? (
          <div className="text-center py-8">
            <Shield className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">
              {searchTerm ? 'No matching blacklist entries found' : 'No blacklist entries yet'}
            </p>
            {!searchTerm && (
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                Add entries to prevent specific participants from being auto-created
              </p>
            )}
          </div>
        ) : (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Added By</TableHead>
                  <TableHead>Date</TableHead>
                  {canEdit && <TableHead className="w-[60px]"></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBlacklist.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell>
                      <Badge variant="outline" className="font-normal">
                        <span className="mr-1.5">
                          {ENTRY_TYPE_LABELS[entry.entry_type].icon}
                        </span>
                        {ENTRY_TYPE_LABELS[entry.entry_type].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {entry.value}
                    </TableCell>
                    <TableCell className="text-sm text-gray-600 dark:text-gray-400 max-w-[200px] truncate">
                      {entry.reason || '-'}
                    </TableCell>
                    <TableCell className="text-sm">
                      {entry.created_by_name}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(entry.created_at).toLocaleDateString()}
                    </TableCell>
                    {canEdit && (
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemoveEntry(entry.id)}
                          className="h-8 w-8 p-0"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Info Alert */}
        <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <div className="flex gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-200">
              Blacklisted entries are checked before auto-creation. Patterns support wildcards (*) for flexible matching.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}