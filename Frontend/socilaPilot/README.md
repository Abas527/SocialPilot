# SocialPilot AI

React + TypeScript + Vite presentation website and project-to-content workspace.

## Run locally

Start the FastAPI backend from `Backend/` first:

```bash
uvicorn api.main:app --reload
```

Then start the frontend from this directory:

```bash
npm install
npm run dev
```

Vite proxies the auth, project, social, wallet, tip, export, and health routes to `http://localhost:8000`. To use a different backend URL in the frontend, set `VITE_API_URL` in the frontend environment.

## Workflow

The landing page presents the SocialPilot AI idea, technical approach, developer community, and blockchain payments vision. In the authenticated workspace, creator profiles, follows, explicit feed posts, wallet verification, Sepolia native ETH tips, and the Sepolia creator marketplace are connected to the backend.

The workspace flow is: register and verify your email, sign in, import a public GitHub repository or add project/work notes, analyze the indexed sources, generate and edit post drafts or a case study, review cited excerpts and claim status, save edits, and export a case study as Markdown or PDF. The Overview dashboard can generate a post and case study together in one AI workflow; either asset can also be generated separately. Generation receives the supported findings and their matching source excerpts. Model-written copy is preserved for editing; claim checks flag unsupported or uncertain statements for review instead of silently replacing a complete draft with a fragment. Content Studio also provides post formats (full, concise, technical walkthrough, and project update) and an editable README Markdown draft organized around supported findings, technologies, architecture, implementation decisions, and source references. Installation and usage steps remain for maintainers to fill in and verify; the output is Markdown, not Typst. The workspace theme preference can be switched between light and dark and is saved in the browser. Drafts and case-study summaries can be explicitly shared to the Community feed after review; nothing is posted automatically. Work notes let developers, remote workers, and other individual contributors describe their role and evidence without requiring a public code repository; do not include confidential employer or client information. Community is for shared feed updates and discovering or following creators; public profile settings are managed from the Personal dashboard. The dedicated Wallet page links and verifies an address by message signature, displays Sepolia test balance and received tips, and supports prepared tips whose receipts are verified by the backend. The Marketplace page separates product discovery, seller listings, and verified buyer purchases; it supports plugin, library, and agent listings with direct Sepolia ETH payments to verified seller wallets. Seller-hosted delivery URLs are returned only to verified buyers, but sellers control the URL itself; SocialPilot provides no escrow or refunds.

The authenticated workspace separates personal management from public interaction. The tabbed Personal dashboard organizes account details, creator profile settings, projects, and saved content. Community is focused on the shared feed and discovering other creators; it does not contain personal account or profile editing.

Community is organized into **My space** (compose and manage your own posts) and **Discover & support** (read community updates, find builders, follow them, and open wallet tipping). Wallet is organized into **Wallet & balance**, **Send a tip**, and **Tip activity**. Content Studio separates post setup from draft review and keeps README drafting as a separate content type. Case studies group editing into story, engineering, and outcomes sections. Marketplace opens directly into its tools and management tabs without a promotional hero panel.

The UI uses the endpoints documented by the FastAPI app in `Backend/api/main.py`. Email verification and Sepolia RPC require backend SMTP and `SEPOLIA_RPC_URL` configuration; tips require a browser wallet with Sepolia test ETH.

## Source layout

- `src/App.tsx` coordinates the workspace state and connects pages to API actions.
- `src/pages/HomePage.tsx` is the presentation website entry point.
- `src/landing/` contains the landing page and its independently maintained sections.
- `src/pages/` contains the Personal dashboard, Project Overview, Content Studio, Case Study, Sources, Community, Marketplace, and Wallet screens.
- `src/components/` contains shared layout, import dialog, headings, and evidence UI.
- `src/services/api.ts` contains backend requests and export/download helpers.
- `src/types.ts` defines the shared API and UI types.
- `src/App.css` and `src/index.css` contain the application and global styles.
