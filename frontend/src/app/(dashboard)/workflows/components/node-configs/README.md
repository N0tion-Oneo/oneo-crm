# Workflow Node Configuration Architecture

This directory contains two types of configuration files for workflow nodes:

## 1. Component Configurations (`*NodeConfig.tsx`)

**Purpose**: Rich, interactive UI components with custom features
**Used by**: `NodeConfigurationEnhanced` (for nodes that need specialized UIs)
**Examples**: 
- `EmailNodeConfig.tsx` - Has attachment management, HTML editor, templates
- `WhatsAppNodeConfig.tsx` - Has quick replies, media attachments, interactive buttons
- `ConditionNodeConfig.tsx` - Has visual condition builder with drag-drop

**Features**:
- Custom React components with rich interactions
- Advanced UI elements (file uploaders, visual builders, etc.)
- Direct integration with external services
- Complex state management

## 2. Parameter Configurations (`*ParametersConfig.tsx` or `*Config.tsx`)

**Purpose**: Configuration definitions for the generic parameter-based UI
**Used by**: `NodeParametersTab` (fallback for nodes without specialized UIs)
**Examples**:
- `EmailParametersConfig.tsx` - Simple form fields for email settings
- `HTTPRequestConfig.tsx` - Standard fields for HTTP configuration
- `RecordOperationsConfig.tsx` - CRUD operation parameters

**Features**:
- Declarative configuration objects
- Standard form field types (text, select, boolean, etc.)
- Conditional field visibility
- Expression support
- Validation rules

## Architecture Decision

Nodes use **Component Configurations** when they need:
- Rich UI interactions (drag-drop, visual builders)
- File management (attachments, uploads)
- Complex nested forms
- Custom validation or real-time feedback
- Integration with external services

Nodes use **Parameter Configurations** when they need:
- Simple form-based configuration
- Standard field types
- Basic conditional logic
- Expression/variable support

## How It Works

1. `NodeConfigurationEnhanced` checks `hasSpecializedConfig()` to determine which system to use
2. If the node is in the specialized list → uses Component Configuration
3. Otherwise → uses `NodeParametersTab` with Parameter Configuration

## Adding New Nodes

### For Simple Nodes:
1. Create a parameter config file: `MyNodeParametersConfig.tsx`
2. Export the config function from `index.ts`
3. Add the case in `NodeParametersTab`

### For Complex Nodes:
1. Create both configurations:
   - Component: `MyNodeConfig.tsx` (for rich UI)
   - Parameters: `MyNodeParametersConfig.tsx` (for fallback/reference)
2. Add to `hasSpecializedConfig()` list in `NodeConfigurationEnhanced`
3. Add the render case in `renderSpecializedConfiguration()`

## File Naming Convention

- `*NodeConfig.tsx` - Component configurations (rich UI)
- `*ParametersConfig.tsx` - Parameter configurations (form definitions)
- `*Config.tsx` - Parameter configurations (alternative naming)

## Note on Duplicates

Some nodes have both types of configurations. This is intentional:
- The Component config provides the rich UI experience
- The Parameter config serves as a fallback and reference for field definitions