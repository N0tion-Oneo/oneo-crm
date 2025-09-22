/**
 * CanvasSettings Component
 * Settings panel for workflow canvas configuration
 */

import React, { useState } from 'react';
import { Panel } from 'reactflow';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Settings,
  X,
  RotateCcw,
  Map,
  Grid3x3,
  MousePointer,
  Zap,
  Eye,
  EyeOff
} from 'lucide-react';
import { CanvasSettings as CanvasSettingsType, BackgroundVariant, ConnectionMode } from '../hooks/useCanvasSettings';

interface CanvasSettingsProps {
  settings: CanvasSettingsType;
  onSettingChange: <K extends keyof CanvasSettingsType>(key: K, value: CanvasSettingsType[K]) => void;
  onReset: () => void;
}

export function CanvasSettings({ settings, onSettingChange, onReset }: CanvasSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Settings Button */}
      <Panel position="top-right" className="!top-4 !right-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
          className="shadow-md bg-background"
          title="Canvas Settings (Press '/' to toggle)"
        >
          <Settings className="h-4 w-4" />
        </Button>
      </Panel>

      {/* Settings Panel */}
      {isOpen && (
        <Panel position="top-right" className="!top-14 !right-4 w-80">
          <Card className="shadow-lg">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Canvas Settings
              </h3>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onReset}
                  className="h-8 w-8 p-0"
                  title="Reset to defaults"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsOpen(false)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Settings Content */}
            <ScrollArea className="h-[400px]">
              <div className="p-4 space-y-6">
                {/* Display Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Eye className="h-4 w-4" />
                    Display
                  </div>

                  <div className="space-y-3 pl-6">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="minimap" className="text-sm">
                        MiniMap
                      </Label>
                      <Switch
                        id="minimap"
                        checked={settings.showMiniMap}
                        onCheckedChange={(checked) => onSettingChange('showMiniMap', checked)}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <Label htmlFor="background" className="text-sm">
                        Background
                      </Label>
                      <Switch
                        id="background"
                        checked={settings.showBackground}
                        onCheckedChange={(checked) => onSettingChange('showBackground', checked)}
                      />
                    </div>

                    {settings.showBackground && (
                      <>
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">
                            Background Style
                          </Label>
                          <Select
                            value={settings.backgroundVariant}
                            onValueChange={(value) => onSettingChange('backgroundVariant', value as BackgroundVariant)}
                          >
                            <SelectTrigger className="w-full h-9">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="dots">Dots</SelectItem>
                              <SelectItem value="lines">Lines</SelectItem>
                              <SelectItem value="cross">Cross</SelectItem>
                              <SelectItem value="none">None</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">
                            Background Gap: {settings.backgroundGap}px
                          </Label>
                          <Slider
                            value={[settings.backgroundGap]}
                            onValueChange={([value]) => onSettingChange('backgroundGap', value)}
                            min={10}
                            max={50}
                            step={5}
                            className="w-full"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <Separator />

                {/* Grid & Snapping Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Grid3x3 className="h-4 w-4" />
                    Grid & Snapping
                  </div>

                  <div className="space-y-3 pl-6">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="snap" className="text-sm">
                        Snap to Grid
                      </Label>
                      <Switch
                        id="snap"
                        checked={settings.snapToGrid}
                        onCheckedChange={(checked) => onSettingChange('snapToGrid', checked)}
                      />
                    </div>

                    {settings.snapToGrid && (
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">
                          Grid Size: {settings.gridSize}px
                        </Label>
                        <Slider
                          value={[settings.gridSize]}
                          onValueChange={([value]) => onSettingChange('gridSize', value)}
                          min={10}
                          max={30}
                          step={5}
                          className="w-full"
                        />
                      </div>
                    )}
                  </div>
                </div>

                <Separator />

                {/* Interaction Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <MousePointer className="h-4 w-4" />
                    Interaction
                  </div>

                  <div className="space-y-3 pl-6">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="pan" className="text-sm">
                        Pan on Scroll
                      </Label>
                      <Switch
                        id="pan"
                        checked={settings.panOnScroll}
                        onCheckedChange={(checked) => onSettingChange('panOnScroll', checked)}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <Label htmlFor="selection" className="text-sm">
                        Box Selection
                      </Label>
                      <Switch
                        id="selection"
                        checked={settings.selectionOnDrag}
                        onCheckedChange={(checked) => onSettingChange('selectionOnDrag', checked)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">
                        Connection Mode
                      </Label>
                      <RadioGroup
                        value={settings.connectionMode}
                        onValueChange={(value) => onSettingChange('connectionMode', value as ConnectionMode)}
                      >
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="loose" id="loose" />
                          <Label htmlFor="loose" className="text-sm font-normal">
                            Loose (connect anywhere)
                          </Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="strict" id="strict" />
                          <Label htmlFor="strict" className="text-sm font-normal">
                            Strict (handles only)
                          </Label>
                        </div>
                      </RadioGroup>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Performance Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Zap className="h-4 w-4" />
                    Performance
                  </div>

                  <div className="space-y-3 pl-6">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="animated" className="text-sm">
                        Animated Edges
                      </Label>
                      <Switch
                        id="animated"
                        checked={settings.animatedEdges}
                        onCheckedChange={(checked) => onSettingChange('animatedEdges', checked)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">
                        Zoom Range: {settings.minZoom}x - {settings.maxZoom}x
                      </Label>
                      <div className="flex gap-2 items-center">
                        <span className="text-xs">Min</span>
                        <Slider
                          value={[settings.minZoom]}
                          onValueChange={([value]) => onSettingChange('minZoom', value)}
                          min={0.1}
                          max={0.5}
                          step={0.1}
                          className="flex-1"
                        />
                        <span className="text-xs">Max</span>
                        <Slider
                          value={[settings.maxZoom]}
                          onValueChange={([value]) => onSettingChange('maxZoom', value)}
                          min={1}
                          max={4}
                          step={0.5}
                          className="flex-1"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </ScrollArea>

            {/* Footer with keyboard shortcuts */}
            <div className="p-3 border-t bg-muted/50">
              <p className="text-xs text-muted-foreground">
                Keyboard shortcuts: <kbd>M</kbd> MiniMap, <kbd>G</kbd> Grid, <kbd>/</kbd> Settings
              </p>
            </div>
          </Card>
        </Panel>
      )}
    </>
  );
}