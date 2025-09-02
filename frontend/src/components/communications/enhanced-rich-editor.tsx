'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Color from '@tiptap/extension-color'
import { TextStyle } from '@tiptap/extension-text-style'
import Highlight from '@tiptap/extension-highlight'
import Image from '@tiptap/extension-image'
import Placeholder from '@tiptap/extension-placeholder'
import { 
  Bold, 
  Italic, 
  Underline as UnderlineIcon, 
  Link as LinkIcon,
  List,
  ListOrdered,
  Heading1,
  Heading2,
  Heading3,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Quote,
  Code,
  Image as ImageIcon,
  Palette,
  Highlighter,
  Undo,
  Redo,
  FileCode,
  Eye,
  Minus,
  Type,
  Strikethrough,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useState, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface EnhancedRichEditorProps {
  value: string
  onChange: (html: string) => void
  placeholder?: string
  className?: string
}

const colors = [
  { name: 'Default', value: '' },
  { name: 'Black', value: '#000000' },
  { name: 'Gray', value: '#6B7280' },
  { name: 'Red', value: '#DC2626' },
  { name: 'Orange', value: '#EA580C' },
  { name: 'Yellow', value: '#CA8A04' },
  { name: 'Green', value: '#16A34A' },
  { name: 'Blue', value: '#2563EB' },
  { name: 'Purple', value: '#9333EA' },
  { name: 'Pink', value: '#DB2777' },
]

const highlights = [
  { name: 'None', value: '' },
  { name: 'Yellow', value: '#FEF3C7' },
  { name: 'Green', value: '#D1FAE5' },
  { name: 'Blue', value: '#DBEAFE' },
  { name: 'Purple', value: '#E9D5FF' },
  { name: 'Pink', value: '#FCE7F3' },
  { name: 'Red', value: '#FEE2E2' },
]

const fontSizes = [
  { name: 'Small', value: '12px' },
  { name: 'Normal', value: '14px' },
  { name: 'Medium', value: '16px' },
  { name: 'Large', value: '18px' },
  { name: 'Extra Large', value: '24px' },
  { name: 'Huge', value: '32px' },
]

export function EnhancedRichEditor({ 
  value, 
  onChange, 
  placeholder = 'Write your email...', 
  className = '' 
}: EnhancedRichEditorProps) {
  const [linkUrl, setLinkUrl] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [showSource, setShowSource] = useState(false)
  const [sourceHtml, setSourceHtml] = useState(value)

  const extensions = [
    StarterKit.configure({
      heading: {
        levels: [1, 2, 3],
      },
    }),
    Link.configure({
      openOnClick: false,
      HTMLAttributes: {
        target: '_blank',
        rel: 'noopener noreferrer',
      },
    }),
    Underline,
    TextAlign.configure({
      types: ['heading', 'paragraph'],
    }),
    Highlight.configure({
      multicolor: true,
    }),
    Image.configure({
      HTMLAttributes: {
        class: 'max-w-full h-auto',
      },
    }),
    Placeholder.configure({
      placeholder,
    }),
  ]
  
  // Debug extension loading
  console.log('TextStyle extension:', TextStyle)
  console.log('Color extension:', Color)
  
  // Add TextStyle and Color only if they're properly loaded
  if (TextStyle && typeof TextStyle === 'object') {
    console.log('Adding TextStyle extension')
    extensions.push(TextStyle)
    
    // Only add Color if TextStyle was added
    if (Color && typeof Color === 'object') {
      console.log('Adding Color extension')
      extensions.push(Color.configure ? Color.configure({
        types: ['textStyle'],
      }) : Color)
    }
  } else {
    console.error('TextStyle or Color extensions not loaded properly')
  }

  const editor = useEditor({
    immediatelyRender: false,
    extensions,
    content: value || '<p></p>',
    editorProps: {
      attributes: {
        class: `tiptap-editor p-4 bg-white dark:bg-gray-900 focus:outline-none ${className}`,
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      onChange(html)
      if (!showSource) {
        setSourceHtml(html)
      }
    },
    onCreate: ({ editor }) => {
      // Debug: Check what commands are available
      console.log('Editor commands available:', {
        setColor: typeof editor.commands.setColor,
        unsetColor: typeof editor.commands.unsetColor,
        setMark: typeof editor.commands.setMark,
        unsetMark: typeof editor.commands.unsetMark,
      })
      
      // Check if TextStyle mark is registered
      console.log('Marks registered:', editor.schema.marks)
    },
  })

  // Update editor content when value prop changes
  useEffect(() => {
    if (editor && value !== editor.getHTML() && !editor.isFocused) {
      editor.commands.setContent(value || '<p></p>')
      setSourceHtml(value || '')
    }
  }, [value, editor])

  const addLink = useCallback(() => {
    if (linkUrl && editor) {
      editor.chain().focus().setLink({ href: linkUrl }).run()
      setLinkUrl('')
    }
  }, [editor, linkUrl])

  const removeLink = useCallback(() => {
    if (editor) {
      editor.chain().focus().unsetLink().run()
    }
  }, [editor])

  const addImage = useCallback(() => {
    if (imageUrl && editor) {
      editor.chain().focus().setImage({ src: imageUrl }).run()
      setImageUrl('')
    }
  }, [editor, imageUrl])

  const setTextColor = useCallback((color: string) => {
    if (editor) {
      console.log('Available color commands:', {
        setColor: typeof editor.commands.setColor,
        unsetColor: typeof editor.commands.unsetColor,
        addMark: typeof editor.commands.addMark,
        removeMark: typeof editor.commands.removeMark,
      })
      
      if (color === '') {
        // Try different approaches
        if (editor.commands.unsetColor) {
          editor.chain().focus().unsetColor().run()
        } else if (editor.commands.removeMark) {
          editor.chain().focus().removeMark('textStyle').run()
        }
      } else {
        // Try different approaches
        if (editor.commands.setColor) {
          editor.chain().focus().setColor(color).run()
        } else if (editor.commands.setMark) {
          editor.chain().focus().setMark('textStyle', { color }).run()
        }
      }
    }
  }, [editor])

  const setHighlightColor = useCallback((color: string) => {
    if (editor) {
      if (color === '') {
        editor.chain().focus().unsetHighlight().run()
      } else {
        editor.chain().focus().toggleHighlight({ color }).run()
      }
    }
  }, [editor])

  const handleSourceEdit = useCallback((newHtml: string) => {
    setSourceHtml(newHtml)
    if (editor) {
      editor.commands.setContent(newHtml)
      onChange(newHtml)
    }
  }, [editor, onChange])

  const insertHorizontalRule = useCallback(() => {
    if (editor) {
      editor.chain().focus().setHorizontalRule().run()
    }
  }, [editor])

  const clearFormatting = useCallback(() => {
    if (editor) {
      editor.chain().focus().clearNodes().unsetAllMarks().run()
    }
  }, [editor])

  if (!editor) {
    return null
  }

  return (
    <div className="border rounded-lg">
      {/* Toolbar */}
      <div className="border-b p-2 flex flex-wrap items-center gap-1 bg-gray-50 dark:bg-gray-800">
        {/* Text Style Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-1">
              <Type className="w-4 h-4" />
              Style
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => editor.chain().focus().setParagraph().run()}>
              Normal Text
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}>
              Heading 1
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>
              Heading 2
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}>
              Heading 3
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleBlockquote().run()}>
              Quote
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleCodeBlock().run()}>
              Code Block
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Separator orientation="vertical" className="h-6" />

        {/* Text formatting */}
        <Button
          type="button"
          variant={editor.isActive('bold') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Bold (Ctrl+B)"
        >
          <Bold className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('italic') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Italic (Ctrl+I)"
        >
          <Italic className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('underline') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          title="Underline (Ctrl+U)"
        >
          <UnderlineIcon className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('strike') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          title="Strikethrough"
        >
          <Strikethrough className="w-4 h-4" />
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Text Color - only show if commands are available */}
        {editor?.commands?.setColor && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" title="Text Color">
                <Palette className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {colors.map((color) => (
                <DropdownMenuItem
                  key={color.value}
                  onClick={() => setTextColor(color.value)}
                className="flex items-center gap-2"
              >
                <div 
                  className="w-4 h-4 rounded border" 
                  style={{ backgroundColor: color.value || '#ffffff' }}
                />
                {color.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Highlight Color */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" title="Highlight">
              <Highlighter className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {highlights.map((color) => (
              <DropdownMenuItem
                key={color.value}
                onClick={() => setHighlightColor(color.value)}
                className="flex items-center gap-2"
              >
                <div 
                  className="w-4 h-4 rounded border" 
                  style={{ backgroundColor: color.value || 'transparent' }}
                />
                {color.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Separator orientation="vertical" className="h-6" />

        {/* Lists */}
        <Button
          type="button"
          variant={editor.isActive('bulletList') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          title="Bullet List"
        >
          <List className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive('orderedList') ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          title="Numbered List"
        >
          <ListOrdered className="w-4 h-4" />
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Alignment */}
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'left' }) ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('left').run()}
          title="Align Left"
        >
          <AlignLeft className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'center' }) ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('center').run()}
          title="Align Center"
        >
          <AlignCenter className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'right' }) ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('right').run()}
          title="Align Right"
        >
          <AlignRight className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'justify' }) ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('justify').run()}
          title="Justify"
        >
          <AlignJustify className="w-4 h-4" />
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Link */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant={editor.isActive('link') ? 'secondary' : 'ghost'}
              size="sm"
              title="Add Link"
            >
              <LinkIcon className="w-4 h-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="space-y-2">
              <Label>URL</Label>
              <Input
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                placeholder="https://example.com"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addLink()
                  }
                }}
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={addLink}>Add Link</Button>
                {editor.isActive('link') && (
                  <Button size="sm" variant="outline" onClick={removeLink}>Remove Link</Button>
                )}
              </div>
            </div>
          </PopoverContent>
        </Popover>

        {/* Image */}
        <Popover>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              title="Add Image"
            >
              <ImageIcon className="w-4 h-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="space-y-2">
              <Label>Image URL</Label>
              <Input
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="https://example.com/image.jpg"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addImage()
                  }
                }}
              />
              <Button size="sm" onClick={addImage}>Add Image</Button>
            </div>
          </PopoverContent>
        </Popover>

        <Separator orientation="vertical" className="h-6" />

        {/* Special */}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={insertHorizontalRule}
          title="Horizontal Line"
        >
          <Minus className="w-4 h-4" />
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Undo/Redo */}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()}
          title="Undo (Ctrl+Z)"
        >
          <Undo className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()}
          title="Redo (Ctrl+Y)"
        >
          <Redo className="w-4 h-4" />
        </Button>

        <Separator orientation="vertical" className="h-6" />

        {/* Source/Preview toggle */}
        <Button
          type="button"
          variant={showSource ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => setShowSource(!showSource)}
          title={showSource ? 'Visual Editor' : 'HTML Source'}
        >
          {showSource ? <Eye className="w-4 h-4" /> : <FileCode className="w-4 h-4" />}
        </Button>
      </div>

      {/* Editor */}
      <div className="h-[250px] overflow-y-auto bg-white dark:bg-gray-900 rounded-b-lg">
        {showSource ? (
          <textarea
            className="w-full h-full p-4 font-mono text-sm bg-transparent outline-none resize-none"
            value={sourceHtml}
            onChange={(e) => handleSourceEdit(e.target.value)}
            placeholder="Enter HTML..."
          />
        ) : (
          <div className="h-full">
            <EditorContent editor={editor} className="outline-none h-full" />
          </div>
        )}
      </div>
    </div>
  )
}