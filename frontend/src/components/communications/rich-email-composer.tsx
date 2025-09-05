'use client'

import { useEditor, EditorContent } from '@tiptap/react'
// BubbleMenu temporarily removed - needs separate installation
// import { BubbleMenu } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
// Table extensions - to be added later
// import Table from '@tiptap/extension-table'
// import TableRow from '@tiptap/extension-table-row'
// import TableCell from '@tiptap/extension-table-cell'
// import TableHeader from '@tiptap/extension-table-header'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Color from '@tiptap/extension-color'
import { TextStyle } from '@tiptap/extension-text-style'
import Highlight from '@tiptap/extension-highlight'
import { 
  Bold, 
  Italic, 
  Underline as UnderlineIcon, 
  Link as LinkIcon,
  List,
  ListOrdered,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  Heading1,
  Heading2,
  Heading3,
  Quote,
  Code,
  Image as ImageIcon,
  // Table as TableIcon,
  Palette,
  Highlighter,
  Undo,
  Redo,
  Eye,
  EyeOff,
  FileCode
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useState, useCallback, useEffect } from 'react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface RichEmailComposerProps {
  value: string
  onChange: (html: string) => void
  placeholder?: string
  className?: string
}

export function RichEmailComposer({ 
  value, 
  onChange, 
  placeholder = 'Write your email...', 
  className = '' 
}: RichEmailComposerProps) {
  const [showSource, setShowSource] = useState(false)
  const [sourceHtml, setSourceHtml] = useState(value)
  const [linkUrl, setLinkUrl] = useState('')
  const [imageUrl, setImageUrl] = useState('')

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
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
      Image.configure({
        HTMLAttributes: {
          class: 'email-image',
        },
      }),
      // Table.configure({
      //   resizable: true,
      // }),
      // TableRow,
      // TableHeader,
      // TableCell,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Underline,
      TextStyle,
      Color,
      Highlight.configure({
        multicolor: true,
      }),
    ],
    content: value || '<p></p>',
    editorProps: {
      attributes: {
        class: `prose prose-sm max-w-none focus:outline-none min-h-[200px] p-4 bg-white dark:bg-gray-900 ${className}`,
        style: 'min-height: 200px;',
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      onChange(html)
      if (!showSource) {
        setSourceHtml(html)
      }
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
    if (linkUrl) {
      editor?.chain().focus().setLink({ href: linkUrl }).run()
      setLinkUrl('')
    }
  }, [editor, linkUrl])

  const removeLink = useCallback(() => {
    editor?.chain().focus().unsetLink().run()
  }, [editor])

  const addImage = useCallback(() => {
    if (imageUrl) {
      editor?.chain().focus().setImage({ src: imageUrl }).run()
      setImageUrl('')
    }
  }, [editor, imageUrl])

  const insertTable = useCallback(() => {
    // Table extension not installed - functionality disabled
    // editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }, [editor])

  const setColor = useCallback((color: string) => {
    editor?.chain().focus().setColor(color).run()
  }, [editor])

  const setHighlight = useCallback((color: string) => {
    editor?.chain().focus().toggleHighlight({ color }).run()
  }, [editor])

  const handleSourceEdit = useCallback((newHtml: string) => {
    setSourceHtml(newHtml)
    if (editor) {
      editor.commands.setContent(newHtml)
      onChange(newHtml)
    }
  }, [editor, onChange])

  if (!editor) {
    return null
  }

  return (
    <div className="border rounded-lg">
      {/* Toolbar */}
      <div className="border-b p-2 flex flex-wrap items-center gap-1">
        {/* Text formatting */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant={editor.isActive('bold') ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleBold().run()}
            title="Bold"
          >
            <Bold className="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive('italic') ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            title="Italic"
          >
            <Italic className="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive('underline') ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            title="Underline"
          >
            <UnderlineIcon className="w-4 h-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-6" />

        {/* Headings */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant={editor.isActive('heading', { level: 1 }) ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            title="Heading 1"
          >
            <Heading1 className="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive('heading', { level: 2 }) ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            title="Heading 2"
          >
            <Heading2 className="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive('heading', { level: 3 }) ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            title="Heading 3"
          >
            <Heading3 className="w-4 h-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-6" />

        {/* Lists */}
        <div className="flex items-center gap-1">
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
        </div>

        <Separator orientation="vertical" className="h-6" />

        {/* Alignment */}
        <div className="flex items-center gap-1">
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
        </div>

        <Separator orientation="vertical" className="h-6" />

        {/* Insert elements */}
        <div className="flex items-center gap-1">
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

          {/* Table - temporarily disabled */}
          {/* <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={insertTable}
            title="Insert Table"
          >
            <TableIcon className="w-4 h-4" />
          </Button> */}

          {/* Quote */}
          <Button
            type="button"
            variant={editor.isActive('blockquote') ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            title="Quote"
          >
            <Quote className="w-4 h-4" />
          </Button>

          {/* Code block */}
          <Button
            type="button"
            variant={editor.isActive('codeBlock') ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            title="Code Block"
          >
            <Code className="w-4 h-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-6" />

        {/* Colors */}
        <div className="flex items-center gap-1">
          {/* Text Color */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                title="Text Color"
              >
                <Palette className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setColor('#000000')}>Black</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setColor('#DC2626')}>Red</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setColor('#16A34A')}>Green</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setColor('#2563EB')}>Blue</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setColor('#9333EA')}>Purple</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setColor('#EA580C')}>Orange</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Highlight */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                title="Highlight"
              >
                <Highlighter className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setHighlight('#FEF3C7')}>Yellow</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setHighlight('#DBEAFE')}>Blue</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setHighlight('#D1FAE5')}>Green</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setHighlight('#FCE7F3')}>Pink</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setHighlight('#E9D5FF')}>Purple</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Separator orientation="vertical" className="h-6" />

        {/* Undo/Redo */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Undo"
          >
            <Undo className="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Redo"
          >
            <Redo className="w-4 h-4" />
          </Button>
        </div>

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
      <div className="min-h-[300px] max-h-[500px] overflow-y-auto bg-white dark:bg-gray-900 border-x border-b rounded-b-lg">
        {showSource ? (
          <textarea
            className="w-full h-full min-h-[300px] p-4 font-mono text-sm bg-transparent"
            value={sourceHtml}
            onChange={(e) => handleSourceEdit(e.target.value)}
            placeholder="Enter HTML..."
          />
        ) : (
          <div className="min-h-[300px]">
            <EditorContent editor={editor} />
          </div>
        )}
      </div>

      {/* Floating menu for quick formatting - BubbleMenu temporarily disabled */}
      {/* {editor && !showSource && (
        <BubbleMenu editor={editor} tippyOptions={{ duration: 100 }}>
          <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border p-1 flex items-center gap-1">
            <Button
              type="button"
              variant={editor.isActive('bold') ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              <Bold className="w-3 h-3" />
            </Button>
            <Button
              type="button"
              variant={editor.isActive('italic') ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              <Italic className="w-3 h-3" />
            </Button>
            <Button
              type="button"
              variant={editor.isActive('underline') ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => editor.chain().focus().toggleUnderline().run()}
            >
              <UnderlineIcon className="w-3 h-3" />
            </Button>
          </div>
        </BubbleMenu>
      )} */}
    </div>
  )
}