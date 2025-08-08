# Field Configuration Architecture - Three-Tier System

## Overview

This document outlines the three-tier architecture for field configuration in the Oneo CRM system, providing clear separation of concerns between field creation, business logic, and form validation.

## Three-Tier Architecture

### **Tier 1: Field Creation**
**Purpose**: Create and configure field types with rich backend configurations  
**Database**: No validation at DB level - pure storage  
**Focus**: Leverage the sophisticated backend field type system  
**Current Implementation Priority**: ✅ **ACTIVE PHASE**

#### Field Configuration by Type

**Text Fields**:
- Min/max length limits - WE DO NOT NEED A LIMIT HERE - HARD CAP AT 160 CHARACTERS
- Default values - WE DO NOT NEED THIS AS AN OPTION
- Case sensitivity options 
- Auto-formatting rules

**Textarea Fields**:
- Number of visible rows (1-20) - - WE DO NOT NEED THIS AS AN OPTION - ROW VISIBLITY SHOULD ADJUST ON CONTENT
- Resize options (none, both, horizontal, vertical) - WE DO NOT NEED THIS AS AN OPTION - SHOULD HAVE FIXED WIDTH AND ADJUST HEIGHT BASED ON CONTENT 
- Rich text editor toggle 
- Min/max length validation - WE DO NOT NEED THIS AS AN OPTION

**Number Fields**:
- Format selection: integer, decimal, currency, percentage, auto-increment
- Decimal places configuration
- Currency codes and display format
- Auto-increment: prefix, starting number, zero padding
- Thousands separator toggle

**Select/Multiselect Fields**:
- Dynamic options management (add/remove/reorder)
- Value and label configuration
- Allow custom values toggle 
- Default selection settings 

**Date Fields**:
- Include time toggle
- Date format (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD)
- Time format (12h/24h)
- Default values (none/today/tomorrow) 
- Default time when date selected

**AI Generated Fields**:
- Model selection (GPT-4.1, GPT-4.1-mini, O3, etc.)
- Prompt templates with field reference system
- Temperature control (0-1)
- Output type (text, number, tags, URL, JSON)
- Tools enablement (web search, code interpreter, DALL-E, etc.)
- Auto-regenerate on field changes
- Cache duration settings
- Editable output toggle

**Phone Fields**:
- Default country selection
- Allowed countries restriction
- Format display toggle
- Country code requirements
- Validation strictness levels - WE DO NOT NEED THIS AS AN OPTION _ VALIDATION HAPPENS AT FORM LEVEL

**Email Fields**:
- Auto-lowercase conversion
- Whitespace trimming
- Domain suggestions (future) - WE DO NOT NEED THIS AS AN OPTION 

**Address Fields**:
- Format: single-line, multi-line, structured
- Component visibility (street, apartment, city, state, postal, country)
- Geocoding enablement
- Default country WE DO NOT NEED THIS AS AN OPTION
- Address validation requirements
- Display format options

**URL Fields**:
- Protocol validation and auto-addition
- Open in new tab behavior
- Favicon display
- Preview on hover
- Whitespace trimming

**File Fields**:
- Allowed file types
- Maximum file size limits
- Upload path configuration
- File type restrictions

**Tags Fields**:
- Predefined tags management
- Allow custom tags toggle
- Maximum tags limit
- Case sensitivity settings

**Relation Fields**:
- Target pipeline selection
- Display field specification
- Allow multiple selections - WE DO NOT NEED THIS AS AN OPTION
- Reverse field naming

**Button Fields**:
- Button text and styling
- Workflow integration
- Confirmation dialogs
- Role-based visibility and permissions
- Size and color options

**Boolean Fields**:
- Default value
- Display labels (Yes/No, True/False, etc.)

#### Basic Settings (All Field Types)
- Field label with auto-generated slug
- Field description
- Help text for users
- Placeholder text - WE DO NOT NEED THIS AS AN OPTION
- Display width (quarter/half/full) - WE DO NOT NEED THIS AS AN OPTION
- Visibility in list view 
- Visibility in detail view
- Search indexing flag
- Display order

### **Tier 2: Business Rules**
**Purpose**: Define field behavior based on pipeline stages and conditions  
**Implementation Priority**: 🔄 **FUTURE PHASE**

#### Stage-Based Requirements
- Visual matrix showing which pipeline stages require this field
- Stage selector interface (Lead → Qualified → Proposal → Closed → Won/Lost)
- Per-stage requirement configuration
- Stage transition validation rules

#### Conditional Logic
- Field dependencies ("If Type = Enterprise, then Company field required")
- Cross-field validation rules
- Dynamic field visibility based on other field values
- Conditional requirement chains

#### Business Logic Settings
- Required/optional status per pipeline stage
- Block stage transitions vs show warnings
- Custom warning messages for missing data
- Validation behavior configuration
- Exception handling rules

#### Examples
- **Kanban Stage Field**: Different fields required for different stages
- **Lead Type**: Enterprise leads require company info, individual leads don't
- **Deal Size**: Large deals require additional approval fields
- **Priority Level**: High priority items require justification text

### **Tier 3: Form Builder**
**Purpose**: Create internal and public forms with advanced validation  
**Implementation Priority**: 🔮 **FUTURE PHASE**

#### Form Types
**Internal Forms**:
- Team data entry forms
- Record update workflows
- Approval process forms
- Administrative interfaces

**Public Forms**:
- Lead capture forms
- Contact forms
- Survey and feedback forms
- Application submissions

#### Advanced Validation (Form Level)
**Input Validation**:
- Regex pattern matching
- Custom validation rules
- Format-specific validation
- Real-time validation feedback

**Range Validation**:
- Min/max values for numbers
- Date range restrictions
- Text length limits
- File size constraints

**Cross-Field Validation**:
- Field dependency checking
- Conditional validation logic
- Multi-field consistency rules
- Complex business rules

**Format Validation**:
- Email format verification
- Phone number validation
- URL structure checking
- Address format validation

**Business Validation**:
- Duplicate record checking
- External API validation
- Database integrity checks
- Custom business logic

#### Form Features
- Multi-step forms with progress indicators
- Conditional field display/hide logic
- Save as draft functionality
- Form analytics and completion tracking
- A/B testing capabilities
- Mobile-responsive design
- Accessibility compliance

## Current Implementation Focus

### **Phase 1: Tier 1 Field Configuration Panel**

**Immediate Goals**:
1. Create comprehensive field type configuration interface
2. Expose ALL rich backend field configurations
3. Provide excellent UX for field creation
4. Maintain clean separation from business rules and forms

**Panel Structure**:

1. **Basic Field Settings Section**
   - Field identity (label, slug, description)
   - Display configuration (width, visibility)
   - User guidance (help text, placeholder)

2. **Field Type Configuration Section**
   - Dynamic panel that adapts to selected field type
   - Type-specific configuration options
   - Real-time preview of field behavior
   - Integration with global options (currencies, countries)

3. **Display & Behavior Section**
   - Layout settings (width, positioning)
   - Visibility controls (list view, detail view)
   - Search and indexing options
   - Display order management

**What NOT to Include in Current Phase**:
- ❌ Business rules configuration (Tier 2)
- ❌ Form validation setup (Tier 3)
- ❌ Database-level constraints (we don't do DB validation)
- ❌ Stage-based requirements
- ❌ Conditional field logic

### **Technical Implementation Details**

**Component Architecture**:
- Main `FieldConfigurationEditor` component
- Specialized configuration panels per field type
- Reusable form components and validation
- Integration with existing field builder UI

**State Management**:
- Single source of truth for field configuration
- Real-time validation with debounced updates
- Optimistic UI updates with error rollback

**Backend Integration**:
- Leverage existing field type definitions from `field_types.py`
- Use Pydantic validation schemas
- Proper error handling and user feedback
- Integration with global options API

## Future Phase Planning

### **Phase 2: Business Rules Interface (Tier 2)**
- Stage requirement matrix builder
- Conditional logic interface
- Business rule validation
- Pipeline integration

### **Phase 3: Form Builder System (Tier 3)**
- Form designer interface
- Advanced validation builder
- Public form generation
- Form analytics dashboard

## Benefits of This Architecture

**Clear Separation of Concerns**:
- Each tier has a distinct, well-defined purpose
- No overlap or confusion between field creation, business logic, and forms
- Clean upgrade path for future features

**Scalability**:
- Can enhance each tier independently
- Maintains backward compatibility
- Supports complex enterprise use cases

**User Experience**:
- Progressive complexity - start simple, add sophistication as needed
- Context-appropriate interfaces for each use case
- Intuitive workflow progression

**Technical Benefits**:
- Maintainable codebase with clear boundaries
- Reusable components across tiers
- Testable architecture with isolated concerns
- Integration-friendly design

## Success Metrics

**Tier 1 Success Criteria**:
- ✅ All 16 backend field types fully configurable
- ✅ Rich configuration options exposed and usable
- ✅ Excellent user experience for field creation
- ✅ Clean foundation for future tier implementation

**Overall Architecture Success**:
- Clear mental model for users
- Efficient development workflow
- Maintainable and extensible codebase
- Supports both simple and complex use cases