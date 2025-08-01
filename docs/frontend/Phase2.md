Phase 2: CRM Core – Pipelines & Records

Prompt:

"Develop pipeline configuration and record management systems. Use schema-driven UI to display and manage CRM records with advanced filtering, inline editing, and real-time updates. Use Next.js 15 and TypeScript."

Objectives:

Build pipeline editor with 18+ field types

Support field visibility, ordering, and templates

Render schema-based record lists with filters

Enable record creation, editing, history, and tags

Handle thousands of records with virtual scrolling

Enforce role-based field visibility and required fields per pipeline stage

Prepare records to embed communications, AI, and workflow context

Functions (Detailed):

Schema builder with field type palette (text, number, date, tags, AI field, etc.)

Pipeline template loader with ability to clone and fork templates

JSONB-based filter system with multi-criteria support (e.g. status: open AND assigned_to: Josh)

Record list view with column sorting, visibility toggles, bulk select + actions

Record detail drawer with inline editing, autosave, and field-level validation

Version history viewer with restore options

Tag assignment, color-coded badges, and tag filter chips

Stage-based schema enforcement: required/hidden/locked fields per stage

Define record-level relationship data (linked records, related threads, workflow runs)

Fetch and display real-time communications thread inside the record view

Record activity feed (field edits, comments, stage changes, system logs)

Sync pipeline stage changes over WebSocket to all viewers of the record

Inherit AI configuration from tenant when generating summaries, auto fields, or workflows

UI Flows:

Pipeline Builder Flow

Admin creates new pipeline → names and adds field definitions → sets stage visibility rules → saves and previews sample form

Record List View

User selects pipeline → views paginated record list → applies filters → sorts columns → selects records for bulk action

Record Detail Flow

User clicks record → detail drawer opens → fields rendered based on stage visibility + user role → inline edits auto-saved → change triggers live update

Stage Change Flow

User updates stage via dropdown → system checks required fields → missing fields prompt inline warning → on valid update: syncs over WebSocket, triggers workflow

Record Thread/Activity Flow

User views comms tab → fetches linked Unipile threads → views inbox-style messages

Switches to Activity tab → sees history timeline with field edits, comments, workflow events

