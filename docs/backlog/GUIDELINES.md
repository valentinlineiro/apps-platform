# 📜 Backlog Management Guidelines

To keep the roadmap organized for both humans and AI, follow these naming and categorization rules.

## 🏷 Naming Convention
Every backlog item must follow the pattern:  
`Category-Number - Title.md`

**Examples:**
- `B-001 - Stripe Integration.md`
- `T-001 - Database Migration.md`
- `U-001 - Dashboard Redesign.md`

## 📂 Categories
- **`B` (Business/Feature)**: New product features and business logic.
- **`T` (Technical/Infrastructure)**: DevOps, architectural refactoring, performance improvements.
- **`U` (UX/UI)**: Design improvements, accessibility, and styling.

## 🔢 Sequential Numbering
- Numbers should be sequential within the category (e.g., `B-001`, `B-002`, `B-003`).
- Always use a 3-digit number (e.g., `001` instead of `1`).

## ✍️ Creating New Items
1.  **Select a Category**: Choose the most relevant prefix (B/T/U).
2.  **Determine the Next Number**: Check the `docs/backlog/` directory for the latest number in that category.
3.  **Use the Template**: Copy the contents of `docs/backlog/AI_TASK_TEMPLATE.md` to ensure the task is "AI-Ready."
4.  **Update Index**: Always add the new file to the table in `docs/backlog/index.md`.
