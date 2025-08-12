import * as React from "react"
import {
  Checkbox,
  Slider,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  ArrayManager,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  Separator,
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Popover,
  PopoverContent,
  PopoverTrigger,
  RadioGroup,
  RadioGroupItem,
  Toggle,
  Button,
  Label
} from './index'

// Test component to verify all new UI components work
export function TestNewComponents() {
  const [checkboxChecked, setCheckboxChecked] = React.useState(false)
  const [sliderValue, setSliderValue] = React.useState([50])
  const [arrayItems, setArrayItems] = React.useState([
    { id: '1', label: 'Item 1', value: 'item1' },
    { id: '2', label: 'Item 2', value: 'item2' }
  ])
  const [radioValue, setRadioValue] = React.useState('option1')
  const [togglePressed, setTogglePressed] = React.useState(false)

  return (
    <TooltipProvider>
      <div className="p-8 space-y-8 max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">New UI Components Test</h1>
        
        {/* Checkbox */}
        <div className="space-y-2">
          <Label>Checkbox Test</Label>
          <div className="flex items-center space-x-2">
            <Checkbox 
              checked={checkboxChecked}
              onCheckedChange={(checked) => setCheckboxChecked(checked === true)}
              id="test-checkbox"
            />
            <Label htmlFor="test-checkbox">Check me</Label>
          </div>
        </div>

        {/* Slider */}
        <div className="space-y-2">
          <Label>Slider Test (Value: {sliderValue[0]})</Label>
          <Slider
            value={sliderValue}
            onValueChange={setSliderValue}
            max={100}
            step={1}
            className="w-full"
          />
        </div>

        {/* Tooltip */}
        <div className="space-y-2">
          <Label>Tooltip Test</Label>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline">Hover me</Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>This is a tooltip!</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Array Manager */}
        <div className="space-y-2">
          <Label>Array Manager Test</Label>
          <ArrayManager
            items={arrayItems}
            onAdd={(item) => setArrayItems(prev => [...prev, item])}
            onRemove={(index) => setArrayItems(prev => prev.filter((_, i) => i !== index))}
            onUpdate={(index, item) => setArrayItems(prev => prev.map((existing, i) => i === index ? item : existing))}
            placeholder="Add new item"
          />
        </div>

        <Separator />

        {/* Radio Group */}
        <div className="space-y-2">
          <Label>Radio Group Test</Label>
          <RadioGroup value={radioValue} onValueChange={setRadioValue}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="option1" id="option1" />
              <Label htmlFor="option1">Option 1</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="option2" id="option2" />
              <Label htmlFor="option2">Option 2</Label>
            </div>
          </RadioGroup>
        </div>

        {/* Toggle */}
        <div className="space-y-2">
          <Label>Toggle Test</Label>
          <Toggle pressed={togglePressed} onPressedChange={setTogglePressed}>
            Toggle me
          </Toggle>
        </div>

        {/* Collapsible */}
        <div className="space-y-2">
          <Label>Collapsible Test</Label>
          <Collapsible>
            <CollapsibleTrigger asChild>
              <Button variant="outline" className="w-full">
                Click to expand
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 p-4 border rounded">
              This content can be collapsed and expanded!
            </CollapsibleContent>
          </Collapsible>
        </div>

        {/* Accordion */}
        <div className="space-y-2">
          <Label>Accordion Test</Label>
          <Accordion type="single" collapsible>
            <AccordionItem value="item-1">
              <AccordionTrigger>Section 1</AccordionTrigger>
              <AccordionContent>
                Content for section 1
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="item-2">
              <AccordionTrigger>Section 2</AccordionTrigger>
              <AccordionContent>
                Content for section 2
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>

        {/* Popover */}
        <div className="space-y-2">
          <Label>Popover Test</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline">Open popover</Button>
            </PopoverTrigger>
            <PopoverContent>
              <p>This is a popover with some content!</p>
            </PopoverContent>
          </Popover>
        </div>

      </div>
    </TooltipProvider>
  )
}