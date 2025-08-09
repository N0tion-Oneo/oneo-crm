import * as React from "react"
import { Button } from './button'
import { Input } from './input'
import { Trash2, Plus } from 'lucide-react'
import { cn } from "@/lib/utils"

interface ArrayManagerItem {
  id: string
  label: string
  value: any
}

interface ArrayManagerProps {
  items: ArrayManagerItem[]
  onAdd: (item: ArrayManagerItem) => void
  onRemove: (index: number) => void
  onUpdate: (index: number, item: ArrayManagerItem) => void
  placeholder?: string
  addButtonText?: string
  className?: string
}

export function ArrayManager({
  items = [],
  onAdd,
  onRemove,
  onUpdate,
  placeholder = "Add item",
  addButtonText = "Add",
  className
}: ArrayManagerProps) {
  const [newItem, setNewItem] = React.useState('')

  const handleAdd = () => {
    if (newItem.trim()) {
      onAdd({
        id: Date.now().toString(),
        label: newItem,
        value: newItem
      })
      setNewItem('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAdd()
    }
  }

  return (
    <div className={cn("space-y-2", className)}>
      {items.map((item, index) => (
        <div key={item.id} className="flex items-center gap-2">
          <Input
            value={item.label}
            onChange={(e) => onUpdate(index, {...item, label: e.target.value, value: e.target.value})}
            className="flex-1"
            placeholder="Enter value"
          />
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={() => onRemove(index)}
            className="shrink-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <div className="flex items-center gap-2">
        <Input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1"
        />
        <Button
          type="button"
          variant="outline"
          onClick={handleAdd}
          disabled={!newItem.trim()}
          className="shrink-0"
        >
          <Plus className="h-4 w-4 mr-2" />
          {addButtonText}
        </Button>
      </div>
    </div>
  )
}