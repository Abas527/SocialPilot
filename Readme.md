# SocialPilot AI — React Frontend Roadmap

The frontend should make SocialPilot AI feel like a professional project workspace, not just a chat interface with a Generate button.

The core experience is: import real work → understand the project → generate content → review evidence → edit and export.

Since your initial MVP is time-constrained, I recommend React + TypeScript + Vite, with a component library or Tailwind CSS for styling. Keep the frontend focused on one polished end-to-end workflow, and let the backend handle repository ingestion, AI generation, evidence validation, and PDF compilation.

## 1. Recommended frontend stack

[File:React.svg - Wikimedia Commons](https://images.openai.com/static-rsc-4/7xLwZ4scX4fnuMMhGGC1cqLT77iXYre5xJdgpd7WX1KQ_p3g1RPDF7yr_WadpTqTOOQqdyWXwfoJZwqVjziB4ZjkWfqXFUA5ZzmEP0gz1yPlo8186Lx7bp_RlOKNJMYunWYIIcau9pEjVKeCiiL7F2AY3pRccI_LGvBv9WXSfHU?purpose=inline)

React + TypeScript + Vite

Build reusable components, type your API responses, and get a fast local development environment.

Core application

[Tailwind CSS Wordmark Logo PNG Vector (SVG) Free Download in 2025 | Word mark logo, Css, Vector logo](https://images.openai.com/static-rsc-4/iecL2Ab__eIJwMwWSQ0fsqaBOaRDQFYLB-PDmu7IyVB8sQq_th1AxXOVxgdKZ0__waTfGwLIHYI4No0nWeY3abP5vL0ik4OIKb_SFE1RmSR6viDxHB2N5Jlaoxv7T0mE1rB805ZIq_i5LMEB_tcI-NrF_idJ0XCmapBO7bf09Bs?purpose=inline)

Tailwind CSS

Implement consistent spacing, typography, colors, responsive layouts, and reusable design patterns.

Styling

[Shadcn UI](https://images.openai.com/static-rsc-4/Wym8MNeEVYc0VXXngIj56tQjmELdCst6FYhviIbVLWQEGN3N_DCubiyyVs9UtaYDryAsraJDxlMAzuHEm1RDyWTpoiPvGk8zMeh38WGtV0E-zzK2dB4GktdnY9rI0f7eOwoPcR7eSHl5gIy5Sd2Yu-wGSduqxMeu60dH_ron0n0?purpose=inline)

shadcn/ui + Lucide icons

Use ready-made dialogs, tabs, buttons, dropdowns, and tooltips rather than designing every primitive yourself.

UI components

[TanStack Query : The Smarter Way to Fetch and Manage Server Data in React | by Matthew Adiorho | Medium](https://images.openai.com/static-rsc-4/XDTtlo919MdA48gNxKoakCAoehNd0yw4Xx8CkZ_COXg8wxVP2pZDWLfR8DccMcXWEURKiNmxfHyCHn4m5xJHxa-ktadPl3CoFEHwzZM4_8hrPHrBs4PLcswD_3frfncApjxzsLXO4QT2BEtgMd_A-ox8UPD4PEu3q2znsBjBKpw?purpose=inline)

TanStack Query + native fetch

Manage API requests, loading states, errors, and refetching. Use ordinary React state for local edits and selected tabs.

Server state

For the first version, you do not need Redux, a complex global state manager, a microfrontend architecture, or a rich-text editor framework. Start with React state and a small API layer; introduce more tools only when needed.

## 2. Design the main user journey

1\. Import Project

GitHub URL or pasted Markdown

2\. Review Project Profile

Technologies, architecture, decisions, limitations

3\. Generate Content

Three LinkedIn drafts and a case study

4\. Review and Edit

Inspect source evidence and fix unsupported claims

5\. Export

Markdown, text, and professional PDF

The interface should make the next action obvious at every step. Users should not need to understand the AI pipeline to use the product.

## 3. Plan the pages and screens

Build one main workspace with a few supporting screens. Avoid building a separate page for every small interaction.

[Project Management Web App Dashboard by Oyasim Ahmed for Zain's Studio on Dribbble](https://images.openai.com/static-rsc-4/xgW0R9J0anPmhzBJ8w4znJgrLC_-OkvxzjH2uoH_lMha_klu_gHOqCrOcajiIwuqayWlORS1kZFAfxSQtU0qbxqB4Jdt51sJtS7oDwAlAjwSppz1g5vK8q_bNeGJQaz5NAZjVgO9DNCHZedGO1zJxpsuAYjhrvRp7TD9oamCGlo?purpose=inline)

Screen A — Dashboard

Route: `/`

- Welcome message and New Project button.
- Recent projects.
- Project status: Imported, Analyzed, Drafts Ready.
- Quick access to previously generated work.

[Introducing the new v0 - Vercel](https://images.openai.com/static-rsc-4/TPgWHhmv7G5kEknOwrZj4OCQhrU_gKimhBMzjPvwNN-rJgJSd08mnxVRFwcsIBbnfIrasfi0wMuGOjsD701E5fp99A9XzqBVx5t1717nsD3fls6PLYsbWDCGwAqTwa4nQ5wjoCXVLcOyTmFZBxJQR--3ZM8piXrq_jHrpAiKj84?purpose=inline)

Screen B — New Project

Route: `/projects/new`

- GitHub URL input.
- Markdown paste area.
- Import and Analyze button.
- Source preview and validation errors.

[Barnacles App - A desktop app for developers](https://images.openai.com/static-rsc-4/2nq4CzvAD0dx_f0rzY0032S6UaQRqZIK3lrPivMef8zGl2WXHXvM9zk9FuAgCFCXf1JtAe07anNtcLcH6-5LHttKrMcIe4_JfoZaKlSqGbzpisLzugUBhNCbbkw0hE7VVMr4FaKZJ2JxuB7BVg-CWqdxz4ciYP2mDZhkiqmFyAc?purpose=inline)

Screen C — Project Workspace

Route: `/projects/:projectId`

- Project summary and technologies.
- Architecture and engineering decisions.
- Results, limitations, and unknowns.
- Source files and evidence references.
- Generate Content button.

[AI LinkedIn Ghostwriter That Sounds Like You | VERSO](https://images.openai.com/static-rsc-4/o0vEQ8sX1JBEj93ew2swvuymhgTGbDZ3X9nRq8HkkdmHAtSIVfDUURgm1Ru3gV1Tow5S-Viv_tOUv7RKTDORKRqBIWZ8res3qgKMiBV6rF7eZXwwjt7PaxvMAsO6bGr3e9uqcEsJct3BoBm2JmZUN_Knw11biLZxdYZ8ayXkKb0?purpose=inline)

Screen D — Content Studio

Route: `/projects/:projectId/content`

- Three LinkedIn draft tabs.
- Case study tab.
- Editable content fields.
- Regenerate, copy, save, and export controls.
- Evidence panel with claim statuses.

### Recommended layout for the Content Studio

Use a three-part layout on desktop:

SocialPilot AI

Project workspace

Content

Technical lesson

Engineering decision

Personal reflection

Case study

Editor

Your draft title

Editable post content appears here. Review and refine the language before exporting.

Save changes · Regenerate

Evidence

Supported

README.md

Source excerpt and repository link.

Review

Illustrative layout. On mobile, stack the editor and evidence panel vertically.

The editor should receive the most screen space. Evidence is important, but it shouldn't make writing feel cramped. On small screens, show evidence in a drawer or collapsible panel.

## 4. Build the frontend in six phases

### Phase 1 — Bootstrap the application

Estimated time: 45 minutes

Create the React project:

```
npm create vite@latest socialpilot-frontend -- --template react-ts
cd socialpilot-frontend
npm install
npm install react-router-dom @tanstack/react-query
npm install lucide-react
npm run dev
```

Set up Tailwind CSS and shadcn/ui using their current installation instructions. Their setup steps can change between versions, so use the instructions for the version you install rather than copying an old configuration.

Create these initial folders:

```
src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers.tsx
├── components/
│   ├── layout/
│   └── ui/
├── features/
│   ├── projects/
│   ├── ingestion/
│   ├── generation/
│   ├── editor/
│   ├── evidence/
│   └── export/
├── lib/
│   ├── api.ts
│   └── utils.ts
├── types/
│   └── index.ts
├── main.tsx
└── index.css
```

Use feature-based organization: project components stay together, content-generation components stay together, and shared layout components live separately.

Deliverable: React application runs, routes load, and the project structure is ready.

### Phase 2 — Build the dashboard and project import

Estimated time: 1 hour 15 minutes

Implement:

- A sidebar or top navigation.
- A recent-projects grid.
- A New Project dialog or page.
- A GitHub URL field.
- A Markdown input area.
- Input validation and loading indicators.

Define a project type:

```
export interface Project {
  id: string;
  name: string;
  repositoryUrl?: string;
  status: "imported" | "analyzed" | "generated";
  createdAt: string;
}
```

Start with mock projects while designing the dashboard. Then connect the UI to the backend when its API is ready.

Use an explicit empty state when no projects exist, such as “Import your first project to create your professional content.”

Deliverable: The user can navigate the dashboard and submit project input.

### Phase 3 — Connect the backend and show the project profile

Estimated time: 1 hour 15 minutes

Create a centralized API client instead of calling `fetch()` independently from every component.

```
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function analyzeProject(input: {
  repositoryUrl?: string;
  readme?: string;
}) {
  const response = await fetch(`${API_BASE_URL}/api/projects/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(`Analysis failed: ${response.status}`);
  }

  return response.json();
}
```

This assumes you create the endpoint shown in the example. Match the URL and request shape to your actual backend implementation.

Add an environment file:

```
VITE_API_BASE_URL=http://localhost:8000
```

Do not put secrets in `VITE_` environment variables; they are exposed to browser code.

Build the project profile screen with cards or sections for:

- Summary and problem.
- Technologies and architecture.
- Engineering decisions.
- Results and limitations.
- Unknowns and source documents.

Add loading, error, and retry states. If the backend returns a profile successfully, the page should transition into the analyzed-project view.

Deliverable: A real project can be imported and its structured profile displayed.

### Phase 4 — Build the Content Studio

Estimated time: 1 hour 45 minutes

This is the most important frontend phase.

Create reusable components:

- `ContentTabs`
- `LinkedInDraftEditor`
- `CaseStudyEditor`
- `EvidencePanel`
- `ClaimStatus`
- `RegenerateButton`
- `ExportMenu`

Use controlled React state for the current edits. Keep the generated version separate from the user's edited version so regeneration doesn't silently erase their changes.

A useful TypeScript model:

```
export interface EvidenceReference {
  sourceId: string;
  path: string;
  excerpt: string;
  sourceUrl?: string;
}

export interface ContentClaim {
  id: string;
  text: string;
  status: "supported" | "needs_review" | "unsupported";
  evidence: EvidenceReference[];
}

export interface ContentDraft {
  id: string;
  kind:
    | "technical_lesson"
    | "engineering_decision"
    | "personal_reflection"
    | "case_study";
  title: string;
  content: string;
  claims: ContentClaim[];
}
```

Make the claim status labels visually clear but restrained. Clicking a claim should reveal its source excerpt and link, where available.

For generation, the frontend should request the desired output type from the backend. It should not contain the AI prompt or model credentials.

Deliverable: Users can switch between content types, edit drafts, inspect evidence, and regenerate a selected draft.

### Phase 5 — Save, copy, and export

Estimated time: 45 minutes

Add three primary actions:

- Save: persist edits to the backend.
- Copy: copy the selected draft to the clipboard.
- Export: download Markdown or request PDF generation.

For Markdown downloads, the frontend can create a Blob from the edited content. For PDFs, prefer a backend endpoint that returns the compiled file rather than recreating the Typst document in the browser.

Handle export errors without losing the current draft. Show a success message only after the operation actually succeeds.

Deliverable: The user can save their edits and download usable files.

### Phase 6 — Responsive design and testing

Estimated time: 1 hour

Test the complete journey:

1. Open the dashboard.
2. Import a repository.
3. Wait for analysis to finish.
4. Open the project profile.
5. Generate content.
6. Edit a draft.
7. Open a claim's evidence.
8. Save changes.
9. Export the case study.
10. Reload the page and check persistence.

Also test:

- Invalid URLs.
- Network failures.
- Empty AI responses.
- Long posts and long file paths.
- Small laptop screens and mobile widths.
- Repeated clicks on generation buttons.
- Switching tabs while an edit is in progress.

Deliverable: The interface handles the main workflow and common failure states.

## 5. Frontend and backend API contract

Agree on the endpoints before wiring every component. This will make integrating your React frontend with the Python backend much easier.

| Method  | Endpoint                                | Purpose                                   |
| ------- | --------------------------------------- | ----------------------------------------- |
| `GET`   | `/api/projects`                         | List saved projects                       |
| `POST`  | `/api/projects/analyze`                 | Import and analyze a repository or README |
| `GET`   | `/api/projects/{id}`                    | Retrieve project profile and sources      |
| `POST`  | `/api/projects/{id}/generate`           | Generate drafts and case study            |
| `PATCH` | `/api/artifacts/{id}`                   | Save user edits                           |
| `POST`  | `/api/artifacts/{id}/regenerate`        | Regenerate a selected artifact            |
| `GET`   | `/api/artifacts/{id}/evidence`          | Retrieve claim evidence                   |
| `GET`   | `/api/artifacts/{id}/export?format=md`  | Download Markdown                         |
| `GET`   | `/api/artifacts/{id}/export?format=pdf` | Download PDF                              |

These are proposed API contracts, not existing endpoints. Define their request and response schemas with your backend before implementation.

For the first version, you can simplify the contract further by returning the project profile directly from the analyze request and returning all generated drafts from one generation request.

## 6. Recommended React component hierarchy

Use a hierarchy like this to keep the code maintainable:

```

App
├── AppLayout
│   ├── Sidebar
│   ├── Topbar
│   └── RouteView
│       ├── DashboardPage
│       │   ├── ProjectCard
│       │   └── NewProjectButton
│       ├── NewProjectPage
│       │   ├── GitHubImportForm
│       │   └── MarkdownImportForm
│       ├── ProjectWorkspacePage
│       │   ├── ProjectSummary
│       │   ├── TechnologyList
│       │   └── SourceFileList
│       └── ContentStudioPage
│           ├── ContentTabs
│           ├── DraftEditor
│           ├── CaseStudyEditor
│           ├── EvidencePanel
│           └── ExportMenu

```

Don't put all the UI, API calls, and editing logic into `App.tsx`. Keep page components responsible for composing the interface and feature components responsible for specific interactions.

## 7. State management: what goes where?

For this MVP, keep it simple.

| State                      | Recommended location           |
| -------------------------- | ------------------------------ |
| Selected tab               | Local React state              |
| Unsaved draft edits        | Editor component or page state |
| Saved projects             | TanStack Query                 |
| Project profile            | TanStack Query                 |
| Generation status          | Mutation state                 |
| Evidence panel open/closed | Local React state              |
| API base URL               | Environment configuration      |
| Persistent content         | Backend database               |

Avoid persisting unsaved sensitive project content in browser storage by default. Save it to your backend only with clear user expectations, and provide a local or private deployment option later if that fits your product direction.

## 8. Suggested design system

For SocialPilot AI, I'd use a restrained developer-tool aesthetic:

SocialPilot AI

Work-to-content workspace

Design direction

Color palette

Charcoal

Warm gray

Indigo

Success green

Design principles

- Spacious editor with readable typography.
- Minimal cards and subtle borders.
- Clear status labels for source verification.
- Consistent buttons and form controls.
- Responsive sidebar that becomes a drawer on mobile.

Use one primary accent color for actions and reserve green or amber for meaningful status indicators. Don't make every section colorful; the content itself should be the focus.

## 9. Priority checklist for your first frontend release

## Implementation tracker

0/14 tasks

Foundation

Create React + TypeScript + Vite app

Configure routing and shared layout

Set up styling and reusable UI components

Project workflow

Build dashboard and empty state

Implement GitHub/Markdown import form

Display structured project profile

Content Studio

Build three LinkedIn draft tabs

Build case study editor

Display claim statuses and evidence

Implement edit and regenerate actions

Export and reliability

Save edits through backend API

Copy and download Markdown

Integrate PDF download

Handle loading, errors, and responsive layout

## My final recommendation

Build the frontend in this order:

1. Dashboard and import form — establish the user journey.
2. Project profile — show what the AI understood from the source.
3. Content Studio — build the core editing experience.
4. Evidence panel — establish trust and differentiate the product.
5. Export and persistence — make the output useful beyond the browser.
6. Polish and responsive behavior — refine the experience after the core path works.

For your initial MVP, the most important screen is the Content Studio. That's where SocialPilot AI proves its value: it turns actual engineering work into content the user can inspect, edit, trust, and reuse.