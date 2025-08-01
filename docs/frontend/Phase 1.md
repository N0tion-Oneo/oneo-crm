Phase 1: Core Infrastructure & Access

Prompt:

"Implement foundational infrastructure for a multi-tenant CRM platform. Set up authentication, tenant lifecycle, permissions, and responsive layout. Use Next.js 15 with App Router, TypeScript, secure cookie sessions, and real-time WebSocket support."

Objectives:

Enable JWT login/logout, session renewal

Detect and isolate tenants from domain/subdomain

Configure tenant branding, domains, AI settings

Implement RBAC and field/action permissions with upstream visibility filters

Build a responsive shell layout with sidebar and dark mode

Establish foundations for real-time data updates and cross-phase socket handling

Set up scaffolding for record-embedded communication and AI context inheritance

Functions (Detailed):

Implement AuthContext for session management with hooks for useLogin, useLogout, useSessionRefresh

Middleware to attach JWT tokens to outgoing requests

Domain-based tenant detection with dynamic config loading

Tenant CRUD UI: create, update, delete, list tenants with logos and brand settings

AI config per tenant: OpenAI key, max token usage, model preference (stored per tenant, inherited by records and workflows)

Permissions UI: matrix of actions vs user roles with granular toggles, defines visibility per pipeline/record field/action

Layout shell with collapsible sidebar, topbar, breadcrumb navigation, dark/light mode toggle, and user avatar menu

WebSocket gateway with JWT-based channel auth: supports downstream modules (record updates, pipeline sync, comm threads)

Initial WebSocket subscription client to allow joining per-record and per-tenant channels

Define context structure to associate communications with records via upstream message metadata

Field access/validation derived upfront based on user role and pipeline stage (supporting stage-dependent schema rules from Phase 2)

User management UI: admin can invite users, assign roles, and resend activation links within tenant scope

Email invite system with tokenized activation links to onboard new users

UI Flows:

Login / Session Flow

User lands on login page → submits credentials → JWT issued → tenant and user role context resolved → redirected to dashboard

Tenant Setup Flow

Admin creates tenant → uploads logo, sets domain/slug, configures AI keys → system provisions WebSocket namespace and default permissions

Permissions Flow

Admin navigates to Permissions → selects user type → views/edit field/action matrix (per pipeline) → updates saved via API with debounce

Layout Shell

Authenticated layout wraps all pages → sidebar menu generated based on permissions → routes switch via App Router → dark mode toggle persists via localStorage

User Onboarding Flow

Admin opens Users panel → clicks "Invite User" → inputs email + selects role → invite sent with link

User receives email → clicks invite → sets name/password → completes registration → redirected into tenant environment

